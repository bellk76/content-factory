from dataclasses import replace

import pytest

from app.config import settings as app_settings
from app.graph.build import run_pipeline
from app.kb.storage import Store
from app.llm.client import MockLLM
from app.services.publisher import Publisher


def _dry_settings():
    return replace(
        app_settings,
        publish_dry_run=True,
        telegram_bot_token="",
        telegram_chat_id="",
        youtube_client_id="",
        youtube_client_secret="",
        youtube_refresh_token="",
    )


def test_pipeline_end_to_end(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    run = run_pipeline("кухонные фасады", "Тестовый бренд", store=store)

    assert run["status"] == "done"
    assert run["review_status"] == "awaiting_approval"
    assert run["script"]["title"]
    assert run["script"]["hook"]
    assert run["content"]["description"]
    assert run["montage"]["timeline"]  # агент монтажа отработал
    assert run["qa"]["passed"] is True
    assert isinstance(run["publish"], list)
    assert {p["platform"] for p in run["publish"]} == {"youtube", "telegram", "device_farm"}
    assert run["analytics"]["views"] > 0
    agents = {s["agent"] for s in store.get_steps(run["id"])}
    assert {"research", "script", "generate", "montage", "qa", "publish", "analytics"} <= agents


class FlakyQALLM(MockLLM):
    """Первый прогон QA — провал, второй — успех. Проверяем цикл доработки."""

    def __init__(self) -> None:
        self.qa_calls = 0

    def complete(self, system, user, schema):
        if schema.__name__ == "QAReport":
            self.qa_calls += 1
            if self.qa_calls == 1:
                return {
                    "passed": False,
                    "score": 40.0,
                    "issues": [{"severity": "high", "message": "нет CTA", "fix": "добавить CTA"}],
                }
            return {"passed": True, "score": 90.0, "issues": []}
        return super().complete(system, user, schema)


def test_qa_loop_forces_revision(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    run = run_pipeline("входные двери", store=store, llm=FlakyQALLM())
    assert run["iteration"] == 2  # сработал цикл: QA -> доработка -> QA
    assert run["status"] == "done"
    assert run["review_status"] == "awaiting_approval"


class BadLLM(MockLLM):
    """Возвращает пустой dict — не проходит валидацию схемы."""

    def complete(self, system, user, schema):
        return {}


def test_invalid_llm_output_marks_error(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    with pytest.raises(Exception):
        run_pipeline("плохая тема", store=store, llm=BadLLM())
    runs = store.list_runs()
    assert runs[0]["status"] == "error"
    assert runs[0]["error"]


def test_fallback_harness(monkeypatch, tmp_path):
    from app.graph import build as gb

    monkeypatch.setattr(gb, "build_langgraph", lambda pipeline: None)
    store = Store(str(tmp_path / "t.db"))
    run = gb.run_pipeline("тестовая тема", store=store)
    assert run["status"] == "done"
    assert run["montage"]["timeline"]


def test_feedback_loop_writes_knowledge(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    run_pipeline("входные двери", store=store)
    assert store.best_knowledge(limit=1)  # хук сохранён в базу знаний


def test_publisher_dry_run_and_device_farm():
    pub = Publisher(_dry_settings())
    tg = pub.publish("текст", "telegram")
    assert tg["status"] == "dry_run"
    farm = pub.publish("текст", "device_farm")
    assert farm["status"] == "queued"


def test_youtube_dry_run_without_keys():
    pub = Publisher(_dry_settings())
    yt = pub.publish("текст", "youtube", video=None, title="Тест")
    assert yt["status"] == "dry_run"
    assert yt["platform"] == "youtube"


def test_render_is_noop_when_disabled(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    run = run_pipeline("без рендера", store=store)  # RENDER_VIDEO=false по умолчанию
    assert run["video"] in (None, "")
    assert run["status"] == "done"
