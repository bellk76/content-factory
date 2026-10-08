"""Загрузка готового ролика на YouTube.

Пример:
    set YOUTUBE_CLIENT_ID=... & set YOUTUBE_CLIENT_SECRET=... & set YOUTUBE_REFRESH_TOKEN=...
    set PUBLISH_DRY_RUN=false
    python scripts/upload_reel.py --video data/reel.mp4 --title "Двери тест" --privacy private
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.services.youtube import YouTubeUploader


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", default="data/reel.mp4")
    parser.add_argument("--title", default="Двери тест")
    parser.add_argument("--description", default="Демо-ролик content-factory")
    parser.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    args = parser.parse_args()

    uploader = YouTubeUploader(settings)
    if not uploader.configured or settings.publish_dry_run:
        print("Режим dry-run (нет ключей или PUBLISH_DRY_RUN=true). Ничего не отправлено.")
    result = uploader.upload(args.video, args.title, args.description, privacy=args.privacy)
    print(result)


if __name__ == "__main__":
    main()
