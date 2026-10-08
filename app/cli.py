"""CLI конвейера.

Примеры:
    python -m app.cli run --topic "входные двери" --brand "Фабрика Браво"
    python -m app.cli list
    python -m app.cli show --id 1
"""

from __future__ import annotations

import argparse
import json

from app.config import settings
from app.graph import build
from app.kb.storage import Store


def _cmd_run(args: argparse.Namespace) -> None:
    run = build.run_pipeline(args.topic, args.brand)
    print(f"[engine={build.ENGINE}] run #{run['id']} status={run['status']} score={run.get('score')}")
    if run.get("script"):
        print("Заголовок:", run["script"].get("title"))
        print("Хук:", run["script"].get("hook"))
    if run.get("content"):
        print("Описание:", run["content"].get("description"))
    if args.json:
        print(json.dumps(run, ensure_ascii=False, indent=2))


def _cmd_list(args: argparse.Namespace) -> None:
    store = Store(settings.db_path)
    for r in store.list_runs(args.limit):
        print(f"#{r['id']:<4} {r['status']:<18} score={r.get('score')} {r['topic']}")


def _cmd_show(args: argparse.Namespace) -> None:
    store = Store(settings.db_path)
    run = store.get_run(args.id)
    if run is None:
        print("Прогон не найден")
        return
    print(json.dumps(run, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="content-factory CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="запустить конвейер по теме")
    p_run.add_argument("--topic", required=True)
    p_run.add_argument("--brand", default="")
    p_run.add_argument("--json", action="store_true", help="печать полного результата")
    p_run.set_defaults(func=_cmd_run)

    p_list = sub.add_parser("list", help="список прогонов")
    p_list.add_argument("--limit", type=int, default=50)
    p_list.set_defaults(func=_cmd_list)

    p_show = sub.add_parser("show", help="показать прогон")
    p_show.add_argument("--id", type=int, required=True)
    p_show.set_defaults(func=_cmd_show)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
