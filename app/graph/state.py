"""Состояние конвейера, которое прокидывается между агентами."""

from __future__ import annotations

from typing import Any, TypedDict


class ContentState(TypedDict, total=False):
    run_id: int
    topic: str
    brand: str

    # Результаты шагов (JSON-совместимые словари из structured output)
    research: dict[str, Any]
    script: dict[str, Any]
    content: dict[str, Any]
    montage: dict[str, Any]
    qa: dict[str, Any]
    publish: dict[str, Any]
    analytics: dict[str, Any]

    iteration: int
    status: str
