"""Провайдер-агностичный LLM-клиент.

Принципы:
* агент просит у клиента результат строго по Pydantic-схеме (structured output);
* mock-режим работает полностью офлайн и детерминированно — чтобы демо и тесты
  запускались без ключей;
* openai-режим подходит любому OpenAI-совместимому шлюзу (OpenAI, DeepSeek,
  OpenRouter, локальный vLLM/ollama).
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Protocol, Type

from pydantic import BaseModel

from app.config import Settings, settings as default_settings


class LLMClient(Protocol):
    name: str

    def complete(self, system: str, user: str, schema: Type[BaseModel]) -> dict[str, Any]:
        ...


# --------------------------------------------------------------------------- #
# Mock-провайдер (офлайн, без ключей)
# --------------------------------------------------------------------------- #

def _extract_topic(user: str) -> str:
    m = re.search(r"Тема:\s*(.+)", user)
    if m:
        return m.group(1).strip()
    first = user.strip().splitlines()[0] if user.strip() else "товар"
    return first[:120]


def _seed(text: str) -> int:
    return int(hashlib.sha1(text.encode("utf-8")).hexdigest(), 16)


def _pick(pool: list, seed: int, n: int) -> list:
    start = seed % len(pool)
    return [pool[(start + i) % len(pool)] for i in range(n)]


_HOOK_POOL = [
    "5 ошибок, которые совершают при выборе «{t}»",
    "«{t}»: что скрывают продавцы",
    "Сколько на самом деле стоит «{t}» и как не переплатить",
    "«{t}» за 30 секунд: главное, что нужно знать",
    "Почему «{t}» разочаровывает — и как этого избежать",
    "Три мифа о «{t}», в которые верят покупатели",
]
_FACT_POOL = [
    "Средний срок службы — 10+ лет при правильной эксплуатации",
    "На цену влияет не материал, а комплектация и монтаж",
    "Оптовая закупка снижает цену на 15–25%",
    "Скрытые доплаты встречаются у 4 из 10 продавцов",
    "Наличие на складе экономит 2–3 недели ожидания",
]
_ANGLE_POOL = ["экономия", "надёжность", "дизайн и статус", "безопасность", "долговечность", "сервис"]
_TITLE_POOL = [
    "Правда о «{t}»: 3 главных правила выбора",
    "«{t}»: как выбрать и не переплатить",
    "«{t}» за 30 секунд: главное",
    "3 ошибки при выборе «{t}»",
    "«{t}»: что важно знать перед покупкой",
]
_RULES = [
    ("Смотрите на комплектацию, а не только на цену", "руки открывают комплект"),
    ("Проверьте, входит ли монтаж и гарантия", "документы и договор"),
    ("Заказывайте из наличия на складе, без ожидания", "склад, погрузка"),
    ("Сравните условия доставки и подъёма", "курьер и лифт"),
    ("Уточните срок гарантии и сервис", "сервисный центр"),
]
_CAPTION_POOL = [
    "«{t}»: 3 правила, которые экономят деньги",
    "Не покупайте это, пока не посмотрите видео",
    "Как выбрать «{t}» и не переплатить",
    "«{t}» за 30 секунд: коротко о главном",
]


class MockLLM:
    """Детерминированные ответы по схеме. Нужен для офлайн-демо и тестов."""

    name = "mock"

    def complete(self, system: str, user: str, schema: Type[BaseModel]) -> dict[str, Any]:
        topic = _extract_topic(user)
        seed = _seed(topic)
        builder = getattr(self, f"_build_{schema.__name__}", None)
        if builder is None:
            raise NotImplementedError(f"MockLLM не умеет схему {schema.__name__}")
        return builder(topic, seed, user)

    def _build_ResearchResult(self, topic: str, seed: int, user: str) -> dict:
        return {
            "topic": topic,
            "audience": "владельцы частных домов и квартир под ремонт, 30–55 лет",
            "hooks": [h.format(t=topic) for h in _pick(_HOOK_POOL, seed, 3)],
            "facts": _pick(_FACT_POOL, seed, 3),
            "angles": _pick(_ANGLE_POOL, seed, 3),
        }

    def _build_ScriptResult(self, topic: str, seed: int, user: str) -> dict:
        rules = _pick(_RULES, seed, 3)
        scenes = [{"t": 0.0, "text": f"Знакомьтесь: «{topic}». Разберём за 30 секунд.", "visual": "крупный план товара"}]
        t = 6.0
        for text, visual in rules:
            scenes.append({"t": t, "text": text, "visual": visual})
            t += 8.0
        return {
            "title": _TITLE_POOL[seed % len(_TITLE_POOL)].format(t=topic),
            "hook": _HOOK_POOL[seed % len(_HOOK_POOL)].format(t=topic),
            "scenes": scenes,
            "cta": "Напишите «ХОЧУ» — подберём и посчитаем цену за 5 минут.",
            "duration_sec": 30,
        }

    def _build_ContentResult(self, topic: str, seed: int, user: str) -> dict:
        return {
            "description": (
                f"Разбираем, как выбрать «{topic}» без переплат. "
                "Сохраняйте, чтобы не потерять, и задавайте вопросы в комментариях."
            ),
            "hashtags": ["#двери", "#ремонт", "#интерьер", "#полезное"],
            "captions": [c.format(t=topic) for c in _pick(_CAPTION_POOL, seed, 3)],
        }

    def _build_MontageResult(self, topic: str, seed: int, user: str) -> dict:
        return {
            "timeline": [
                {"t": 0.0, "scene": "хук", "asset": "крупный план + титр", "transition": "zoom-in"},
                {"t": 6.0, "scene": "правило 1", "asset": "b-roll: комплект", "transition": "cut"},
                {"t": 14.0, "scene": "правило 2", "asset": "графика: галочки", "transition": "slide"},
                {"t": 22.0, "scene": "правило 3", "asset": "b-roll: склад", "transition": "cut"},
            ],
            "music": "энергичный поп, 110 bpm",
            "captions": True,
            "export": "1080x1920, 30fps, H.264",
        }

    def _build_QAReport(self, topic: str, seed: int, user: str) -> dict:
        # Лёгкий линтер поверх контента: короткий текст или отсутствие CTA = замечание.
        issues: list[dict] = []
        passed = True
        score = 88.0
        if "cta" in user.lower() and "напишите" not in user.lower():
            issues.append({"severity": "medium", "message": "Не найден явный призыв к действию", "fix": "Добавить CTA в финал"})
            passed = False
            score = 60.0
        return {"passed": passed, "score": score, "issues": issues}

    def _build_AnalyticsResult(self, topic: str, seed: int, user: str) -> dict:
        views = 3000 + seed % 7000
        likes = int(views * 0.05)
        comments = int(views * 0.006)
        return {
            "post_id": "mock-post",
            "views": views,
            "likes": likes,
            "comments": comments,
            "ctr": round(1.5 + (seed % 30) / 10.0, 2),
            "summary": "Хук с цифрой сработал лучше среднего; CTA дал заявки в комментариях.",
        }


# --------------------------------------------------------------------------- #
# OpenAI-совместимый провайдер
# --------------------------------------------------------------------------- #

class OpenAICompatibleClient:
    """Любой OpenAI-совместимый /chat/completions эндпоинт."""

    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 60):
        self.name = f"openai:{model}"
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def complete(self, system: str, user: str, schema: Type[BaseModel]) -> dict[str, Any]:
        import requests  # импорт здесь, чтобы mock-режим не требовал сети

        json_schema = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
        system_full = (
            f"{system}\n\n"
            "Верни ТОЛЬКО валидный JSON без markdown, строго по этой JSON-схеме:\n"
            f"{json_schema}"
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_full},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.7,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)


def build_llm(config: Settings | None = None) -> LLMClient:
    cfg = config or default_settings
    if cfg.llm_provider == "openai" and cfg.llm_base_url:
        return OpenAICompatibleClient(cfg.llm_base_url, cfg.llm_api_key, cfg.llm_model)
    return MockLLM()
