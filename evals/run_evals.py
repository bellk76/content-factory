"""Мини-эвал: прогон конвейера по размеченному набору тем.

Проверяем базовые инварианты: QA пропустил контент, все шаги дали результат.
Для mock-режима детерминированно; для реальных моделей — аккуратность по датасету.

Запуск: python -m evals.run_evals
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.graph.build import run_pipeline
from app.kb.storage import Store

DATASET = Path(__file__).parent / "dataset.jsonl"


def main() -> None:
    cases = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    passed = 0
    scores: list[float] = []

    with tempfile.TemporaryDirectory() as tmp:
        store = Store(str(Path(tmp) / "evals.db"))
        for case in cases:
            run = run_pipeline(case["topic"], case.get("brand", ""), store=store)
            qa_ok = bool(run.get("qa", {}).get("passed"))
            has_all = all(run.get(f) for f in ("research", "script", "content", "montage"))
            ok = qa_ok and has_all
            passed += int(ok)
            scores.append(float(run.get("score") or 0))
            print(f"[{'OK' if ok else 'FAIL'}] {case['topic']:<40} score={run.get('score')}")
        store.close()

    n = len(cases)
    print(f"\nПройдено: {passed}/{n}  Средний score: {sum(scores) / n:.1f}")


if __name__ == "__main__":
    main()
