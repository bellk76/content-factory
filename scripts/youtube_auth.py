"""Одноразовое получение YOUTUBE_REFRESH_TOKEN (OAuth2, loopback-флоу).

Перед запуском создайте OAuth-клиент типа «Desktop app» в Google Cloud
(включив YouTube Data API v3) и задайте YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET.

Запуск:
    set YOUTUBE_CLIENT_ID=... & set YOUTUBE_CLIENT_SECRET=...
    python scripts/youtube_auth.py
Откроется браузер -> выберите аккаунт/канал и дайте доступ -> скрипт выведет
refresh_token. Сохраните его в YOUTUBE_REFRESH_TOKEN.
"""

from __future__ import annotations

import argparse
import http.server
import socketserver
import sys
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings

SCOPE = "https://www.googleapis.com/auth/youtube.upload"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id", default=settings.youtube_client_id)
    parser.add_argument("--client-secret", default=settings.youtube_client_secret)
    parser.add_argument("--client-secrets-file", default="", help="скачанный client_secret_*.json из Google Cloud")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    if args.client_secrets_file:
        import json
        block = json.loads(Path(args.client_secrets_file).read_text(encoding="utf-8"))
        block = block.get("installed") or block.get("web") or {}
        args.client_id = args.client_id or block.get("client_id", "")
        args.client_secret = args.client_secret or block.get("client_secret", "")

    if not args.client_id or not args.client_secret:
        print("Нужны YOUTUBE_CLIENT_ID и YOUTUBE_CLIENT_SECRET (env или флаги).")
        return

    redirect = f"http://localhost:{args.port}/"
    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": args.client_id,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    })

    holder: dict[str, str] = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            query = urllib.parse.urlparse(self.path).query
            holder["code"] = urllib.parse.parse_qs(query).get("code", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<h2>Готово — можно закрыть окно.</h2>".encode("utf-8"))

        def log_message(self, *_: object) -> None:
            pass

    httpd = socketserver.TCPServer(("localhost", args.port), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    print("Откройте ссылку и дайте доступ к каналу:\n", url)
    try:
        webbrowser.open(url)
    except Exception:
        pass

    for _ in range(600):
        if holder.get("code"):
            break
        time.sleep(1)
    httpd.shutdown()

    code = holder.get("code")
    if not code:
        print("Код авторизации не получен.")
        return

    import requests

    resp = requests.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": args.client_id,
            "client_secret": args.client_secret,
            "redirect_uri": redirect,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    resp.raise_for_status()
    refresh = resp.json().get("refresh_token")
    if refresh:
        _save_env(args.client_id, args.client_secret, refresh)
        print("\nГотово: токены записаны в .env (YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN).")
    else:
        print("\nrefresh_token пустой — повторите (нужен prompt=consent).")


def _save_env(client_id: str, client_secret: str, refresh_token: str) -> None:
    env = Path(".env")
    lines = env.read_text(encoding="utf-8").splitlines() if env.exists() else []
    updates = {
        "YOUTUBE_CLIENT_ID": client_id,
        "YOUTUBE_CLIENT_SECRET": client_secret,
        "YOUTUBE_REFRESH_TOKEN": refresh_token,
    }
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0].strip()
        if key in updates:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            out.append(line)
    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}={value}")
    env.write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
