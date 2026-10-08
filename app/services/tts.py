"""Синтез речи: адаптер с несколькими провайдерами.

Приоритет: yandex / elevenlabs (нейро-голоса, если есть ключ) -> иначе sapi
(офлайн Windows SAPI, русский голос Irina). Все провайдеры приводятся к WAV
(PCM), чтобы монтаж мог просто склеивать дорожки.

Включение нейро-голоса: TTS_PROVIDER=yandex + YANDEX_API_KEY + YANDEX_FOLDER_ID
или TTS_PROVIDER=elevenlabs + ELEVENLABS_API_KEY (+ ELEVENLABS_VOICE_ID).
"""

from __future__ import annotations

import wave
from pathlib import Path

from app.config import Settings, settings as default_settings


_PIPER_CACHE: dict[str, object] = {}


def synthesize(text: str, out_path: Path, config: Settings | None = None) -> Path:
    cfg = config or default_settings
    provider = cfg.tts_provider
    try:
        if provider == "piper" and Path(cfg.tts_piper_model).exists():
            return _piper(text, out_path, cfg)
        if provider == "yandex" and cfg.tts_yandex_api_key and cfg.tts_yandex_folder_id:
            return _yandex(text, out_path, cfg)
        if provider == "elevenlabs" and cfg.tts_elevenlabs_api_key:
            return _elevenlabs(text, out_path, cfg)
    except Exception:
        # при сбое нейро-провайдера не роняем конвейер — откатываемся на офлайн SAPI
        pass
    return _sapi(text, out_path)


def _piper(text: str, out_path: Path, cfg: Settings) -> Path:
    import wave

    from piper import PiperVoice

    voice = _PIPER_CACHE.get(cfg.tts_piper_model)
    if voice is None:
        voice = PiperVoice.load(cfg.tts_piper_model)
        _PIPER_CACHE[cfg.tts_piper_model] = voice
    with wave.open(str(out_path), "wb") as w:
        voice.synthesize_wav(text, w)  # type: ignore[attr-defined]
    return out_path


def _write_wav(path: Path, pcm: bytes, rate: int = 22050, channels: int = 1, width: int = 2) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(pcm)
    return path


def _sapi(text: str, out_path: Path) -> Path:
    import pyttsx3

    engine = pyttsx3.init()
    for v in engine.getProperty("voices"):
        name = (getattr(v, "name", "") or "").lower()
        if "irina" in name or "russian" in name:
            engine.setProperty("voice", v.id)
            break
    engine.setProperty("rate", 172)
    engine.setProperty("volume", 1.0)
    engine.save_to_file(text, str(out_path))
    engine.runAndWait()
    return out_path


def _yandex(text: str, out_path: Path, cfg: Settings) -> Path:
    import requests

    resp = requests.post(
        "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize",
        headers={"Authorization": f"Api-Key {cfg.tts_yandex_api_key}"},
        data={
            "text": text,
            "lang": "ru-RU",
            "voice": cfg.tts_yandex_voice,
            "format": "lpcm",
            "sampleRateHertz": "22050",
            "folderId": cfg.tts_yandex_folder_id,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return _write_wav(out_path, resp.content, rate=22050)


def _elevenlabs(text: str, out_path: Path, cfg: Settings) -> Path:
    import requests

    voice_id = cfg.tts_elevenlabs_voice_id or "EXAVITQu4vr4xnSDxMaL"  # Sarah (multilingual)
    resp = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=pcm_22050",
        headers={"xi-api-key": cfg.tts_elevenlabs_api_key, "Content-Type": "application/json"},
        json={"text": text, "model_id": "eleven_multilingual_v2"},
        timeout=60,
    )
    resp.raise_for_status()
    return _write_wav(out_path, resp.content, rate=22050)
