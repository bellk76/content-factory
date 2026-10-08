"""Демо-ролик: тонкая обёртка над app.services.video.

Примеры:
    python scripts/video_proof.py --topic "Двери тест" --out data/reel.mp4
    python scripts/video_proof.py                      # последний прогон из БД
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.services.video import render_video

DB_PATH = Path("data/content_factory.db")
DEFAULT_TOPIC = "Двери тест"
DEFAULT_SCENES = [
    "Разберём выбор дверей за 30 секунд",
    "Смотрите на комплектацию, а не только на цену",
    "Проверьте, входит ли монтаж и гарантия",
    "Заказывайте из наличия на складе, без ожидания",
]


def load_script_from_db() -> tuple[str, list[str], str]:
    if not DB_PATH.exists():
        return DEFAULT_TOPIC, DEFAULT_SCENES, ""
    try:
        con = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        row = con.execute(
            "SELECT topic, script FROM runs WHERE script IS NOT NULL ORDER BY id DESC LIMIT 1"
        ).fetchone()
        con.close()
        if not row:
            return DEFAULT_TOPIC, DEFAULT_SCENES, ""
        script = json.loads(row["script"])
        scenes = [s.get("text", "") for s in script.get("scenes", []) if s.get("text")]
        return (row["topic"] or DEFAULT_TOPIC), (scenes or DEFAULT_SCENES), script.get("cta", "")
    except Exception:
        return DEFAULT_TOPIC, DEFAULT_SCENES, ""


def script_for_topic(topic: str) -> tuple[str, list[str], str]:
    from app.graph.build import run_pipeline

    run = run_pipeline(topic, "Bravo")
    script = run.get("script") or {}
    scenes = [s.get("text", "") for s in script.get("scenes", []) if s.get("text")]
    return topic, (scenes or DEFAULT_SCENES), script.get("cta", "")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/reel.mp4")
    parser.add_argument("--topic", default="")
    parser.add_argument("--music-volume", type=float, default=None)
    args = parser.parse_args()

    cfg = settings if args.music_volume is None else replace(settings, music_volume=args.music_volume)

    if args.topic:
        topic, scenes, cta = script_for_topic(args.topic)
    else:
        topic, scenes, cta = load_script_from_db()

    out = render_video(topic, scenes, cta, args.out, cfg)
    size_kb = out.stat().st_size / 1024
    print(f"Готово: {out.resolve()}  ({size_kb:.0f} КБ)  голос: {cfg.tts_provider}  тема: {topic}")
    if cta:
        print(f"CTA: {cta}")


if __name__ == "__main__":
    main()
