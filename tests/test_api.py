"""Тесты API (FastAPI TestClient). Используют временную БД и mock-LLM."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.api.main as main
from app.kb.storage import Store


@pytest.fixture
def client(tmp_path):
    main._store = Store(str(tmp_path / "api.db"))
    return TestClient(main.app)


def _new_run(client: TestClient, topic: str = "тест") -> int:
    resp = client.post("/api/runs", json={"topic": topic, "brand": ""})
    assert resp.status_code == 200
    return int(resp.json()["id"])


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_and_get_run(client):
    rid = _new_run(client)
    r = client.get(f"/api/runs/{rid}")
    assert r.status_code == 200
    assert r.json()["script"]["title"]


def test_topic_validation(client):
    assert client.post("/api/runs", json={"topic": ""}).status_code == 422


def test_get_missing_run_404(client):
    assert client.get("/api/runs/9999").status_code == 404


def test_update_script_and_video_invalidated(client):
    rid = _new_run(client)
    script = {
        "title": "Новый",
        "hook": "Хук",
        "scenes": [{"t": 0, "text": "сцена", "visual": "кадр"}],
        "cta": "CTA",
        "duration_sec": 30,
    }
    r = client.put(f"/api/runs/{rid}/script", json=script)
    assert r.status_code == 200
    assert r.json()["script"]["title"] == "Новый"
    assert not r.json()["video"]  # видео помечено устаревшим


def test_video_404_when_absent(client):
    rid = _new_run(client)
    assert client.get(f"/api/runs/{rid}/video").status_code == 404


def test_settings_platforms_normalized(client):
    r = client.put("/api/settings/platforms", json={"platforms": ["YouTube", "youtube", "vk"]})
    assert r.status_code == 200
    assert r.json()["platforms"] == ["youtube", "vk"]
    assert client.get("/api/settings/platforms").json()["platforms"] == ["youtube", "vk"]


def test_settings_platforms_empty_422(client):
    assert client.put("/api/settings/platforms", json={"platforms": ["   "] * 1}).status_code == 422


def test_list_limit_clamped(client):
    assert client.get("/api/runs?limit=-1").status_code == 422


def test_publish_dry_run(client):
    rid = _new_run(client)
    r = client.post(f"/api/runs/{rid}/publish")
    assert r.status_code == 200
    platforms = {p["platform"] for p in r.json()["publish"]}
    assert platforms
