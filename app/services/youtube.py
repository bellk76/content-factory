"""Загрузка видео на YouTube (Data API v3, OAuth2 канала).

Работает по refresh token: меняем его на access token и вставляем видео
resumable-загрузкой. Если ключи не заданы или включён dry-run — ничего не
отправляем, возвращаем локальный идентификатор.

Нужны переменные окружения: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET,
YOUTUBE_REFRESH_TOKEN.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Optional

from app.config import Settings, settings as default_settings

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


class YouTubeUploader:
    def __init__(self, config: Settings | None = None):
        self.cfg = config or default_settings

    @property
    def configured(self) -> bool:
        return bool(
            self.cfg.youtube_client_id
            and self.cfg.youtube_client_secret
            and self.cfg.youtube_refresh_token
        )

    def upload(
        self,
        video_path: Optional[str],
        title: str,
        description: str = "",
        tags: Optional[list[str]] = None,
        privacy: str = "private",
    ) -> dict[str, Any]:
        if self.cfg.publish_dry_run or not self.configured:
            return {"platform": "youtube", "status": "dry_run", "post_id": f"dry-{uuid.uuid4().hex[:8]}", "url": None}
        if not video_path or not Path(video_path).exists():
            # видео ещё не отрендерено — ставим в очередь
            return {"platform": "youtube", "status": "queued", "post_id": None, "url": None}

        import requests

        # YouTube отклоняет '<' и '>'; стрелки приводим к юникод-виду
        title = title.replace("->", "→").replace("<-", "←").replace("<", "").replace(">", "")
        description = description.replace("->", "→").replace("<-", "←").replace("<", "").replace(">", "")

        token = self._access_token(requests)
        init = requests.post(
            f"{UPLOAD_URL}?uploadType=resumable&part=snippet,status",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": "video/*",
            },
            json={
                "snippet": {"title": title[:95], "description": description[:4900], "tags": tags or [], "categoryId": "22"},
                "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
            },
            timeout=60,
        )
        if init.status_code >= 400:
            return {"platform": "youtube", "status": "error", "post_id": None, "url": None, "detail": init.text[:600]}
        location = init.headers.get("Location")
        if not location:
            return {"platform": "youtube", "status": "error", "post_id": None, "url": None, "detail": "нет Location в ответе"}

        with open(video_path, "rb") as fh:
            data = fh.read()
        up = requests.put(location, headers={"Content-Type": "video/*"}, data=data, timeout=600)
        if up.status_code >= 400:
            return {"platform": "youtube", "status": "error", "post_id": None, "url": None, "detail": up.text[:600]}
        video_id = up.json().get("id")
        return {
            "platform": "youtube",
            "status": "published",
            "post_id": video_id,
            "url": f"https://youtu.be/{video_id}" if video_id else None,
        }

    def _access_token(self, requests) -> str:
        resp = requests.post(
            TOKEN_URL,
            data={
                "client_id": self.cfg.youtube_client_id,
                "client_secret": self.cfg.youtube_client_secret,
                "refresh_token": self.cfg.youtube_refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]
