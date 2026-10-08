"""Хранилище прогонов, промптов и метрик (SQLite).

«Единая база знаний» из требований вакансии: сюда пишутся результаты каждого
шага, метрики публикаций и лучшие кейсы для few-shot (см. retrieval.py).

Потокобезопасность: FastAPI обслуживает запросы в пуле потоков, поэтому доступ
к соединению защищён локом (и чтения, и записи); включён режим WAL.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    topic         TEXT NOT NULL,
    brand         TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL DEFAULT 'running',
    review_status TEXT,
    error         TEXT,
    iteration     INTEGER NOT NULL DEFAULT 0,
    score         REAL,
    research      TEXT,
    script        TEXT,
    content       TEXT,
    montage       TEXT,
    qa            TEXT,
    publish       TEXT,
    analytics     TEXT,
    video         TEXT
);

CREATE TABLE IF NOT EXISTS prompts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    agent       TEXT NOT NULL,
    version     TEXT NOT NULL,
    content     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS metrics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    run_id      INTEGER NOT NULL,
    platform    TEXT NOT NULL,
    post_id     TEXT,
    views       INTEGER DEFAULT 0,
    likes       INTEGER DEFAULT 0,
    comments    INTEGER DEFAULT 0,
    ctr         REAL DEFAULT 0,
    FOREIGN KEY (run_id) REFERENCES runs (id)
);

CREATE TABLE IF NOT EXISTS knowledge (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    run_id      INTEGER NOT NULL,
    topic       TEXT NOT NULL,
    hook        TEXT,
    score       REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS step_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    run_id      INTEGER NOT NULL,
    agent       TEXT NOT NULL,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    ok          INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (run_id) REFERENCES runs (id)
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

_JSON_FIELDS = ("research", "script", "content", "montage", "qa", "publish", "analytics")

# whitelist колонок, которые можно менять через update_run (защита от инъекции имени)
_ALLOWED_UPDATE = {
    "topic", "brand", "status", "review_status", "error", "iteration", "score",
    "research", "script", "content", "montage", "qa", "publish", "analytics", "video",
}


class Store:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        """Добавляет недостающие колонки в существующую БД (без потери данных)."""
        cols = {row["name"] for row in self._conn.execute("PRAGMA table_info(runs)")}
        for name, ddl in (("review_status", "TEXT"), ("error", "TEXT"), ("video", "TEXT")):
            if name not in cols:
                self._conn.execute(f"ALTER TABLE runs ADD COLUMN {name} {ddl}")

    # --------------------------- runs --------------------------- #
    def create_run(self, topic: str, brand: str = "") -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO runs (topic, brand, status) VALUES (?, ?, 'running')",
                (topic, brand),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def update_run(self, run_id: int, **fields: Any) -> None:
        fields = {k: v for k, v in fields.items() if k in _ALLOWED_UPDATE}
        if not fields:
            return
        cols, values = [], []
        for key, value in fields.items():
            if key in _JSON_FIELDS and value is not None and not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            cols.append(f"{key} = ?")
            values.append(value)
        values.append(run_id)
        with self._lock:
            self._conn.execute(f"UPDATE runs SET {', '.join(cols)} WHERE id = ?", values)
            self._conn.commit()

    def get_run(self, run_id: int) -> Optional[dict[str, Any]]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return self._row_to_run(row) if row else None

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_run(r) for r in rows]

    # --------------------------- metrics --------------------------- #
    def save_metrics(self, run_id: int, platform: str, post_id: str | None, data: dict[str, Any]) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO metrics (run_id, platform, post_id, views, likes, comments, ctr) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    platform,
                    post_id,
                    _as_int(data.get("views")),
                    _as_int(data.get("likes")),
                    _as_int(data.get("comments")),
                    _as_float(data.get("ctr")),
                ),
            )
            self._conn.commit()

    def avg_ctr(self) -> float:
        with self._lock:
            row = self._conn.execute("SELECT AVG(ctr) AS c FROM metrics").fetchone()
        return float(row["c"]) if row and row["c"] is not None else 0.0

    # --------------------------- prompts --------------------------- #
    def save_prompt(self, agent: str, version: str, content: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO prompts (agent, version, content) VALUES (?, ?, ?)",
                (agent, version, content),
            )
            self._conn.commit()

    # --------------------------- knowledge --------------------------- #
    def save_knowledge(self, run_id: int, topic: str, hook: str, score: float) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO knowledge (run_id, topic, hook, score) VALUES (?, ?, ?, ?)",
                (run_id, topic, hook, score),
            )
            self._conn.commit()

    def best_knowledge(self, limit: int = 5) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT topic, hook, score FROM knowledge ORDER BY score DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [{"topic": r["topic"], "hook": r["hook"], "score": r["score"]} for r in rows]

    # --------------------------- settings --------------------------- #
    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self._lock:
            row = self._conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            self._conn.commit()

    # --------------------------- step logs --------------------------- #
    def save_step(self, run_id: int, agent: str, duration_ms: int, ok: bool = True) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO step_logs (run_id, agent, duration_ms, ok) VALUES (?, ?, ?, ?)",
                (run_id, agent, duration_ms, 1 if ok else 0),
            )
            self._conn.commit()

    def get_steps(self, run_id: int) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT agent, duration_ms, ok, created_at FROM step_logs WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    # --------------------------- helpers --------------------------- #
    @staticmethod
    def _row_to_run(row: sqlite3.Row) -> dict[str, Any]:
        run = dict(row)
        for field in _JSON_FIELDS:
            if run.get(field):
                try:
                    run[field] = json.loads(run[field])
                except (TypeError, json.JSONDecodeError):
                    pass
        return run

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
