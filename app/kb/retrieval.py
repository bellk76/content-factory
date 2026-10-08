"""Простой retrieval из базы знаний (few-shot для промптов).

Пока это ранжирование по оценке QA + пересечению слов с темой. При росте базы
легко заменить на эмбеддинги и векторный поиск, не меняя интерфейс.
"""

from __future__ import annotations

import re

from app.kb.storage import Store

_WORD = re.compile(r"[a-zA-Zа-яА-ЯёЁ]{3,}")


def _tokens(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(text or "")}


def few_shot_examples(store: Store, topic: str, limit: int = 3) -> list[dict]:
    """Возвращает лучшие прошлые кейсы, релевантные теме (по пересечению слов)."""
    candidates = store.best_knowledge(limit=50)
    topic_tokens = _tokens(topic)
    scored = []
    for c in candidates:
        overlap = len(topic_tokens & _tokens(c.get("topic", "")))
        scored.append((overlap, c.get("score", 0), c))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [c for _, _, c in scored[:limit]]


def render_few_shot(examples: list[dict]) -> str:
    if not examples:
        return "Примеров пока нет."
    lines = ["Удачные прошлые заходы (ориентир по качеству):"]
    for ex in examples:
        lines.append(f"- тема: {ex.get('topic')} | хук: {ex.get('hook')} | оценка: {ex.get('score')}")
    return "\n".join(lines)
