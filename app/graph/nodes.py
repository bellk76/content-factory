"""Узлы конвейера: агенты + контроль качества + публикация и аналитика.

Pipeline — переиспользуемый harness: одни и те же узлы работают и в LangGraph, и
во встроенном fallback-раннере (build.py). Каждый вызов агента проходит через
_run_agent: замер latency, запись в step_logs и ВАЛИДАЦИЯ structured output по
Pydantic-схеме (с одним repair-ретраем).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Type

from pydantic import BaseModel, ValidationError

from app.agents import prompts
from app.config import Settings, settings as default_settings
from app.graph.state import ContentState
from app.kb.retrieval import few_shot_examples, render_few_shot
from app.kb.storage import Store
from app.llm.client import LLMClient, build_llm
from app.llm.schemas import (
    AnalyticsResult,
    ContentResult,
    MontageResult,
    QAReport,
    ResearchResult,
    ScriptResult,
)
from app.services.publisher import Publisher


class Pipeline:
    def __init__(
        self,
        store: Store,
        llm: LLMClient | None = None,
        publisher: Publisher | None = None,
        config: Settings | None = None,
    ):
        self.cfg = config or default_settings
        self.store = store
        self.llm = llm or build_llm(self.cfg)
        self.publisher = publisher or Publisher(self.cfg)

    # --------------------------- инфраструктура --------------------------- #
    def _run_agent(
        self, run_id: int, agent: str, system: str, user: str, schema: Type[BaseModel]
    ) -> dict[str, Any]:
        """Вызвать агента, провалидировать ответ по схеме (с одним repair-ретраем)."""
        start = time.perf_counter()
        ok = True
        try:
            raw = self.llm.complete(system, user, schema)
            try:
                return schema.model_validate(raw).model_dump()
            except ValidationError:
                repair = (
                    f"{user}\n\nВАЖНО: предыдущий ответ не соответствовал JSON-схеме. "
                    "Верни строго валидный JSON по схеме, без markdown."
                )
                raw = self.llm.complete(system, repair, schema)
                return schema.model_validate(raw).model_dump()
        except Exception:
            ok = False
            raise
        finally:
            ms = int((time.perf_counter() - start) * 1000)
            self.store.save_step(run_id, agent, ms, ok)

    def _qa_ok(self, state: ContentState) -> bool:
        qa = state.get("qa", {})
        return bool(qa.get("passed")) and (qa.get("score") or 0) >= self.cfg.qa_min_score

    # ----------------------------- агенты ----------------------------- #
    def research(self, state: ContentState) -> dict[str, Any]:
        examples = few_shot_examples(self.store, state["topic"])
        user = (
            f"Тема: {state['topic']}\n"
            f"Бренд: {state.get('brand', '')}\n\n"
            f"{render_few_shot(examples)}"
        )
        data = self._run_agent(state["run_id"], "research", prompts.RESEARCH_SYSTEM, user, ResearchResult)
        self.store.update_run(state["run_id"], research=data, status="researched")
        return {"research": data, "iteration": 0}

    def script(self, state: ContentState) -> dict[str, Any]:
        parts = [
            f"Тема: {state['topic']}",
            f"Ресёрч: {json.dumps(state.get('research', {}), ensure_ascii=False)}",
        ]
        qa = state.get("qa")
        if qa and not self._qa_ok(state):
            fixes = "; ".join(i.get("fix", "") for i in qa.get("issues", []))
            parts.append(f"Правки от QA, которые нужно учесть: {fixes}")
            self.store.update_run(state["run_id"], status="revising")
        data = self._run_agent(
            state["run_id"], "script", prompts.SCRIPT_SYSTEM, "\n".join(parts), ScriptResult
        )
        self.store.update_run(state["run_id"], script=data)
        return {"script": data}

    def generate(self, state: ContentState) -> dict[str, Any]:
        user = (
            f"Тема: {state['topic']}\n"
            f"Сценарий: {json.dumps(state.get('script', {}), ensure_ascii=False)}"
        )
        data = self._run_agent(
            state["run_id"], "generate", prompts.CONTENT_SYSTEM, user, ContentResult
        )
        self.store.update_run(state["run_id"], content=data)
        return {"content": data}

    def montage(self, state: ContentState) -> dict[str, Any]:
        user = (
            f"Тема: {state['topic']}\n"
            f"Сценарий: {json.dumps(state.get('script', {}), ensure_ascii=False)}"
        )
        data = self._run_agent(
            state["run_id"], "montage", prompts.MONTAGE_SYSTEM, user, MontageResult
        )
        self.store.update_run(state["run_id"], montage=data)
        return {"montage": data}

    def qa(self, state: ContentState) -> dict[str, Any]:
        user = (
            f"Тема: {state['topic']}\n"
            f"Сценарий: {json.dumps(state.get('script', {}), ensure_ascii=False)}\n"
            f"Контент: {json.dumps(state.get('content', {}), ensure_ascii=False)}\n"
            f"Монтаж: {json.dumps(state.get('montage', {}), ensure_ascii=False)}"
        )
        data = self._run_agent(state["run_id"], "qa", prompts.QA_SYSTEM, user, QAReport)
        iteration = int(state.get("iteration", 0)) + 1
        self.store.update_run(
            state["run_id"], qa=data, iteration=iteration, score=data.get("score")
        )
        return {"qa": data, "iteration": iteration}

    def route_after_qa(self, state: ContentState) -> str:
        if self._qa_ok(state) or int(state.get("iteration", 0)) >= self.cfg.max_qa_iterations:
            return "publish"
        return "revise"

    # ------------------------- рендер видео ------------------------- #
    def render(self, state: ContentState) -> dict[str, Any]:
        """Собирает готовый mp4 из сценария (если RENDER_VIDEO включён)."""
        if not self.cfg.render_video:
            return {}
        from app.services.video import render_video

        script = state.get("script", {})
        scenes = [s.get("text", "") for s in script.get("scenes", []) if s.get("text")]
        out = Path(self.cfg.video_dir) / f"run_{state['run_id']}.mp4"
        start = time.perf_counter()
        ok = True
        try:
            render_video(state["topic"], scenes, script.get("cta", ""), out, self.cfg)
            self.store.update_run(state["run_id"], video=str(out))
            return {"video": str(out)}
        except Exception:
            ok = False
            raise
        finally:
            self.store.save_step(
                state["run_id"], "render", int((time.perf_counter() - start) * 1000), ok
            )

    # --------------------------- публикация --------------------------- #
    def _publish_platforms(self) -> list[str]:
        raw = self.store.get_setting("publish_platforms")
        if raw:
            try:
                value = json.loads(raw)
                if isinstance(value, list) and value:
                    return [str(x) for x in value]
            except json.JSONDecodeError:
                pass
        return ["youtube", "telegram", "device_farm"]

    def publish(self, state: ContentState) -> dict[str, Any]:
        content = state.get("content", {})
        parts = [content.get("description", "")]
        if content.get("captions"):
            parts.append(content["captions"][0])
        if state.get("script", {}).get("cta"):
            parts.append(state["script"]["cta"])
        text = "\n\n".join(p for p in parts if p)
        if content.get("hashtags"):
            text = f"{text}\n\n{' '.join(content['hashtags'])}"

        start = time.perf_counter()
        try:
            results = self.publisher.publish_many(
                text,
                platforms=self._publish_platforms(),
                video=state.get("video"),
                title=state.get("script", {}).get("title"),
            )
            ok = True
        except Exception:
            ok = False
            raise
        finally:
            self.store.save_step(
                state["run_id"], "publish", int((time.perf_counter() - start) * 1000), ok
            )

        ok_any = any(r.get("status") in ("published", "dry_run", "queued") for r in results)
        status = "published" if ok_any else "publish_failed"
        fields: dict[str, Any] = {"publish": results, "status": status}
        run = self.store.get_run(state["run_id"]) or {}
        if run.get("review_status") not in ("approved", "rejected"):
            fields["review_status"] = "awaiting_approval" if self._qa_ok(state) else "needs_review"
        self.store.update_run(state["run_id"], **fields)
        return {"publish": results, "status": status}

    def analytics(self, state: ContentState) -> dict[str, Any]:
        publish = state.get("publish", [])
        primary = publish[0] if isinstance(publish, list) and publish else {}
        user = (
            f"Публикации (JSON): {json.dumps(publish, ensure_ascii=False)}\n"
            f"Средний CTR по прошлым постам: {self.store.avg_ctr():.2f}"
        )
        data = self._run_agent(
            state["run_id"], "analytics", prompts.ANALYTICS_SYSTEM, user, AnalyticsResult
        )
        data["post_id"] = primary.get("post_id") or data.get("post_id", "")
        self.store.save_metrics(
            state["run_id"],
            platform=primary.get("platform", "telegram"),
            post_id=data["post_id"],
            data=data,
        )
        # Обратная связь: в базу знаний пишем только прошедший контроль хук.
        hook = state.get("script", {}).get("hook", "")
        score = state.get("qa", {}).get("score", 0) or 0
        if hook and self._qa_ok(state):
            self.store.save_knowledge(state["run_id"], state["topic"], hook, score)
        self.store.update_run(state["run_id"], analytics=data, status="done")
        return {"analytics": data, "status": "done"}

    # ------------------------- fallback-раннер ------------------------- #
    def run_fallback(self, state: ContentState) -> ContentState:
        state.update(self.research(state))
        while True:
            state.update(self.script(state))
            state.update(self.generate(state))
            state.update(self.montage(state))
            state.update(self.qa(state))
            if self.route_after_qa(state) == "publish":
                break
        state.update(self.publish(state))
        state.update(self.analytics(state))
        return state
