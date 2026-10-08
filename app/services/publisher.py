"""Публикация контента: адаптеры площадок.

* YouTube — загрузка видео (OAuth, см. services/youtube.py).
* Telegram — рабочий адаптер (текст или видео, если задан бот-токен).
* VK / заглушки — точки расширения.
* device farm — очередь задач на ферму физических устройств (ADB/Appium).
* dry-run — по умолчанию ничего не отправляем.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Optional

from app.config import Settings, settings as default_settings

DEVICE_FARM_DOC = (
    "Публикация через ферму устройств: очередь задач -> воркер забирает задание -> "
    "поднимает нужный Android-эмулятор/устройство (ADB/Appium) -> выполняет сценарий "
    "публикации в приложении -> снимает метрики."
)


class Publisher:
    def __init__(self, config: Settings | None = None):
        self.cfg = config or default_settings

    def publish_many(
        self, text: str, platforms: list[str], video: Optional[str] = None, title: Optional[str] = None
    ) -> list[dict[str, Any]]:
        return [self.publish(text, p, video=video, title=title) for p in platforms]

    def publish(
        self, text: str, platform: str = "telegram",
        video: Optional[str] = None, title: Optional[str] = None,
    ) -> dict[str, Any]:
        adapter = {
            "youtube": self._youtube,
            "telegram": self._telegram,
            "vk": self._stub,
            "device_farm": self._device_farm,
        }.get(platform)
        if adapter is None:
            return {"platform": platform, "status": "error", "post_id": None, "url": None}
        return adapter(text, platform, video, title)

    # --------------------------- adapters --------------------------- #
    def _youtube(self, text: str, platform: str, video: Optional[str], title: Optional[str]) -> dict[str, Any]:
        from app.services.youtube import YouTubeUploader

        return YouTubeUploader(self.cfg).upload(
            video, title=title or text[:95], description=text
        )

    def _telegram(self, text: str, platform: str, video: Optional[str], title: Optional[str]) -> dict[str, Any]:
        if self.cfg.publish_dry_run or not (self.cfg.telegram_bot_token and self.cfg.telegram_chat_id):
            return {"platform": platform, "status": "dry_run", "post_id": f"dry-{uuid.uuid4().hex[:8]}", "url": None}

        import requests

        base = f"https://api.telegram.org/bot{self.cfg.telegram_bot_token}"
        if video and Path(video).exists():
            with open(video, "rb") as fh:
                resp = requests.post(
                    f"{base}/sendVideo",
                    data={"chat_id": self.cfg.telegram_chat_id, "caption": text[:1000]},
                    files={"video": fh},
                    timeout=300,
                )
        else:
            resp = requests.post(
                f"{base}/sendMessage",
                json={"chat_id": self.cfg.telegram_chat_id, "text": text},
                timeout=30,
            )
        if not (resp.status_code == 200 and resp.json().get("ok")):
            return {"platform": platform, "status": "error", "post_id": None, "url": None}
        return {"platform": platform, "status": "published", "post_id": str(resp.json()["result"]["message_id"]), "url": None}

    def _stub(self, text: str, platform: str, video: Optional[str], title: Optional[str]) -> dict[str, Any]:
        return {"platform": platform, "status": "queued", "post_id": f"{platform}-{uuid.uuid4().hex[:8]}", "url": None}

    def _device_farm(self, text: str, platform: str, video: Optional[str], title: Optional[str]) -> dict[str, Any]:
        return {"platform": platform, "status": "queued", "post_id": f"farm-{uuid.uuid4().hex[:8]}", "url": None}
