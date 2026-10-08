"""Настройки приложения (читаются из окружения / .env)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

_TOKEN_RE = re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}")  # telegram bot token в URL


def redact(text: str) -> str:
    """Маскирует токены/секреты в текстах ошибок."""
    return _TOKEN_RE.sub("<token>", text or "")

try:  # python-dotenv опционален
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - нет зависимости, работаем на переменных окружения
    pass

ROOT = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock").strip().lower()
    llm_base_url: str = os.getenv("LLM_BASE_URL", "").strip()
    llm_api_key: str = os.getenv("LLM_API_KEY", "").strip()
    llm_model: str = os.getenv("LLM_MODEL", "mock").strip()

    db_path: str = os.getenv("DB_PATH", str(ROOT / "data" / "content_factory.db"))

    max_qa_iterations: int = int(os.getenv("MAX_QA_ITERATIONS", "3"))
    qa_min_score: int = int(os.getenv("QA_MIN_SCORE", "70"))

    publish_dry_run: bool = _env_bool("PUBLISH_DRY_RUN", "true")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    # YouTube (OAuth2: client id/secret + refresh token канала)
    # Необязательный API-токен: если задан — мутирующие эндпоинты требуют заголовок x-api-key
    api_token: str = os.getenv("API_TOKEN", "").strip()

    youtube_client_id: str = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
    youtube_client_secret: str = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
    youtube_refresh_token: str = os.getenv("YOUTUBE_REFRESH_TOKEN", "").strip()

    # Рендер видео из сценария
    render_video: bool = _env_bool("RENDER_VIDEO", "false")
    video_dir: str = os.getenv("VIDEO_DIR", str(ROOT / "data" / "videos"))
    assets_dir: str = os.getenv("ASSETS_DIR", str(ROOT / "data" / "assets"))
    music_volume: float = float(os.getenv("MUSIC_VOLUME", "0.16"))

    # Озвучка: piper (офлайн нейро) | sapi (офлайн SAPI) | yandex | elevenlabs
    tts_provider: str = os.getenv("TTS_PROVIDER", "piper").strip().lower()
    tts_piper_model: str = os.getenv("PIPER_MODEL", "data/voices/ru_RU-irina-medium.onnx").strip()
    tts_yandex_api_key: str = os.getenv("YANDEX_API_KEY", "").strip()
    tts_yandex_folder_id: str = os.getenv("YANDEX_FOLDER_ID", "").strip()
    tts_yandex_voice: str = os.getenv("YANDEX_VOICE", "alena").strip()
    tts_elevenlabs_api_key: str = os.getenv("ELEVENLABS_API_KEY", "").strip()
    tts_elevenlabs_voice_id: str = os.getenv("ELEVENLABS_VOICE_ID", "").strip()


settings = Settings()
