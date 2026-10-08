"""FastAPI-приложение: запуск конвейера и рабочее место оператора.

Эндпоинты:
* GET  /api/health
* GET  /api/runs, GET /api/runs/{id}
* POST /api/runs                       — запустить конвейер
* PUT  /api/runs/{id}/script|content|montage
* POST /api/runs/{id}/render           — собрать видео
* GET  /api/runs/{id}/video            — отдать видео
* POST /api/runs/{id}/publish          — опубликовать
* POST /api/runs/{id}/approve|reject
* GET/PUT /api/settings/platforms

Мутирующие эндпоинты при заданном API_TOKEN требуют заголовок `x-api-key`.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.config import redact, settings
from app.graph import build as graph_build
from app.graph.nodes import Pipeline
from app.kb.storage import Store
from app.llm.schemas import ContentResult, MontageResult, ScriptResult
from app.services.video import render_video

app = FastAPI(title="content-factory", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5180",
        "http://127.0.0.1:5180",
        "http://localhost:5173",
    ],
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type", "x-api-key"],
)

DEFAULT_PLATFORMS = ["youtube", "telegram", "device_farm"]

_store: Store | None = None
_store_lock = threading.Lock()


def get_store() -> Store:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = Store(settings.db_path)
    return _store


def require_token(x_api_key: str | None = Header(default=None)) -> None:
    """Если задан API_TOKEN — мутирующие эндпоинты требуют заголовок x-api-key."""
    if settings.api_token and x_api_key != settings.api_token:
        raise HTTPException(status_code=401, detail="unauthorized")


class NewRun(BaseModel):
    topic: str = Field(min_length=1, max_length=300)
    brand: str = Field(default="", max_length=200)


class PlatformsUpdate(BaseModel):
    platforms: list[str] = Field(min_length=1, max_length=20)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "llm": settings.llm_provider, "engine": graph_build.ENGINE}


@app.get("/api/settings/platforms")
def get_platforms() -> dict:
    raw = get_store().get_setting("publish_platforms")
    try:
        platforms = json.loads(raw) if raw else list(DEFAULT_PLATFORMS)
        if not isinstance(platforms, list) or not all(isinstance(x, str) for x in platforms):
            platforms = list(DEFAULT_PLATFORMS)
    except (json.JSONDecodeError, TypeError):
        platforms = list(DEFAULT_PLATFORMS)
    return {"platforms": platforms}


@app.put("/api/settings/platforms", dependencies=[Depends(require_token)])
def set_platforms(payload: PlatformsUpdate) -> dict:
    seen: list[str] = []
    for item in payload.platforms:
        name = item.strip().lower()[:32]
        if name and name not in seen:
            seen.append(name)
    if not seen:
        raise HTTPException(status_code=422, detail="platforms must not be empty")
    get_store().set_setting("publish_platforms", json.dumps(seen, ensure_ascii=False))
    return {"platforms": seen}


@app.get("/api/runs")
def list_runs(limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    return get_store().list_runs(limit)


@app.get("/api/runs/{run_id}")
def get_run(run_id: int) -> dict:
    run = get_store().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@app.post("/api/runs", dependencies=[Depends(require_token)])
def create_run(payload: NewRun) -> dict:
    try:
        return graph_build.run_pipeline(
            payload.topic.strip(), payload.brand.strip(), store=get_store()
        )
    except Exception as exc:  # прогон уже помечен status=error внутри run_pipeline
        raise HTTPException(status_code=500, detail=f"pipeline failed: {redact(str(exc))}") from exc


def _require_run(run_id: int) -> dict:
    run = get_store().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@app.put("/api/runs/{run_id}/script", dependencies=[Depends(require_token)])
def update_script(run_id: int, script: ScriptResult) -> dict:
    store = get_store()
    _require_run(run_id)
    store.update_run(run_id, script=script.model_dump(), video=None)  # видео устарело
    return store.get_run(run_id)  # type: ignore[return-value]


@app.put("/api/runs/{run_id}/content", dependencies=[Depends(require_token)])
def update_content(run_id: int, content: ContentResult) -> dict:
    store = get_store()
    _require_run(run_id)
    store.update_run(run_id, content=content.model_dump())
    return store.get_run(run_id)  # type: ignore[return-value]


@app.put("/api/runs/{run_id}/montage", dependencies=[Depends(require_token)])
def update_montage(run_id: int, montage: MontageResult) -> dict:
    store = get_store()
    _require_run(run_id)
    store.update_run(run_id, montage=montage.model_dump(), video=None)  # видео устарело
    return store.get_run(run_id)  # type: ignore[return-value]


@app.post("/api/runs/{run_id}/render", dependencies=[Depends(require_token)])
def render_run(run_id: int) -> dict:
    """Собрать видео из текущего (возможно отредактированного) сценария."""
    store = get_store()
    run = _require_run(run_id)
    script = run.get("script") or {}
    scenes = [s.get("text", "") for s in script.get("scenes", []) if s.get("text")]
    out = Path(settings.video_dir) / f"run_{run_id}.mp4"
    tmp = out.with_name(f"{out.stem}.tmp{out.suffix}")
    try:
        render_video(run["topic"], scenes, script.get("cta", ""), tmp, settings)
        os.replace(tmp, out)  # атомарная замена
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"render failed: {redact(str(exc))}") from exc
    store.update_run(run_id, video=str(out))
    return store.get_run(run_id)  # type: ignore[return-value]


@app.get("/api/runs/{run_id}/video")
def get_video(run_id: int) -> FileResponse:
    run = _require_run(run_id)
    if not run.get("video"):
        raise HTTPException(status_code=404, detail="video not found")
    base = Path(settings.video_dir).resolve()
    path = Path(run["video"]).resolve()
    if not path.is_file() or base not in path.parents:
        raise HTTPException(status_code=404, detail="video file missing")
    return FileResponse(path, media_type="video/mp4", filename=f"run_{run_id}.mp4")


@app.post("/api/runs/{run_id}/publish", dependencies=[Depends(require_token)])
def publish_run(run_id: int) -> dict:
    """Публикация по кнопке: берём текущий (возможно отредактированный) контент."""
    store = get_store()
    run = _require_run(run_id)
    pipeline = Pipeline(store)
    state = {
        "run_id": run_id,
        "topic": run["topic"],
        "script": run.get("script") or {},
        "content": run.get("content") or {},
        "video": run.get("video"),
        "qa": run.get("qa") or {},
    }
    try:
        pipeline.publish(state)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"publish failed: {redact(str(exc))}") from exc
    return store.get_run(run_id)  # type: ignore[return-value]


@app.post("/api/runs/{run_id}/approve", dependencies=[Depends(require_token)])
def approve(run_id: int) -> dict:
    store = get_store()
    _require_run(run_id)
    store.update_run(run_id, review_status="approved")
    return store.get_run(run_id)  # type: ignore[return-value]


@app.post("/api/runs/{run_id}/reject", dependencies=[Depends(require_token)])
def reject(run_id: int) -> dict:
    store = get_store()
    _require_run(run_id)
    store.update_run(run_id, review_status="rejected")
    return store.get_run(run_id)  # type: ignore[return-value]
