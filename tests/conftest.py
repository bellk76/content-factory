"""Общая настройка тестов: гарантируем безопасный режим (без реальных отправок)."""

import os

# должно стоять до импорта app.config (который читает .env через dotenv)
os.environ["PUBLISH_DRY_RUN"] = "true"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["TELEGRAM_CHAT_ID"] = ""
os.environ["YOUTUBE_CLIENT_ID"] = ""
os.environ["YOUTUBE_CLIENT_SECRET"] = ""
os.environ["YOUTUBE_REFRESH_TOKEN"] = ""
os.environ["API_TOKEN"] = ""
