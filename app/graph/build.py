"""Сборка графа и запуск конвейера.

Основной движок — LangGraph. Если он не установлен, используется встроенный
fallback-harness (Pipeline.run_fallback) с той же логикой и циклом QA.
Это осознанный компромисс: демо запускается где угодно, а не только там, где
поднят LangGraph.

Поток: research -> script -> generate -> montage -> qa -(fail)-> script
                                                            \\-(pass)-> render -> publish -> analytics
"""

from __future__ import annotations

from typing import Any, Optional

from app.config import Settings, redact, settings as default_settings
from app.graph.nodes import Pipeline
from app.graph.state import ContentState
from app.kb.storage import Store
from app.llm.client import LLMClient
from app.services.publisher import Publisher

ENGINE = "langgraph"


def build_langgraph(pipeline: Pipeline) -> Optional[Any]:
    """Собирает граф LangGraph. Возвращает None, если LangGraph недоступен."""
    try:
        from langgraph.graph import END, StateGraph
    except Exception:
        return None

    graph = StateGraph(ContentState)
    graph.add_node("research", pipeline.research)
    graph.add_node("script", pipeline.script)
    graph.add_node("generate", pipeline.generate)
    graph.add_node("montage", pipeline.montage)
    graph.add_node("qa", pipeline.qa)
    graph.add_node("render", pipeline.render)
    graph.add_node("publish", pipeline.publish)
    graph.add_node("analytics", pipeline.analytics)

    graph.set_entry_point("research")
    graph.add_edge("research", "script")
    graph.add_edge("script", "generate")
    graph.add_edge("generate", "montage")
    graph.add_edge("montage", "qa")
    graph.add_conditional_edges(
        "qa", pipeline.route_after_qa, {"revise": "script", "publish": "render"}
    )
    graph.add_edge("render", "publish")
    graph.add_edge("publish", "analytics")
    graph.add_edge("analytics", END)
    return graph.compile()


def run_pipeline(
    topic: str,
    brand: str = "",
    *,
    store: Store | None = None,
    llm: LLMClient | None = None,
    publisher: Publisher | None = None,
    config: Settings | None = None,
) -> dict[str, Any]:
    cfg = config or default_settings
    store = store or Store(cfg.db_path)
    pipeline = Pipeline(store, llm=llm, publisher=publisher, config=cfg)

    run_id = store.create_run(topic, brand)
    state: ContentState = {"run_id": run_id, "topic": topic, "brand": brand, "iteration": 0}

    graph = build_langgraph(pipeline)
    global ENGINE
    try:
        if graph is not None:
            ENGINE = "langgraph"
            state = graph.invoke(state)  # type: ignore[assignment]
        else:
            ENGINE = "fallback"
            state = pipeline.run_fallback(state)
    except Exception as exc:  # терминальный статус вместо «зомби-running»
        store.update_run(run_id, status="error", error=redact(str(exc)))
        raise

    return store.get_run(run_id) or state  # type: ignore[return-value]
