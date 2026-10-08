"""Ролик «о программе»: полный цикл и модели по шагам (горизонтальный, с озвучкой).

Коротко: по каждому шагу — как работает сейчас и какие модели можно подключить.
Переиспользует рендер слайдов из project_demo.py.

Запуск:
    python scripts/project_fullcycle.py --out data/fullcycle.mp4
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import wave
from pathlib import Path

import imageio_ffmpeg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from project_demo import (
    FPS, H, W, _concat_wavs, _wav_duration, make_full_image_slide, make_image_slide, make_slide,
)

from app.config import settings
from app.services.music import generate_music
from app.services.tts import synthesize

SLIDES = [
    (
        "content-factory — веб-приложение",
        ["__FULLIMG__:data/ui_land.png"],
        "Это content-factory — веб-приложение для автоматического производства видео. Вот экран оператора. Покажу полный цикл: как это работает сейчас и какие модели можно подключить на каждом шаге.",
    ),
    (
        "Как пользоваться: вводим тему",
        ["__IMG__:data/ui_step1.png"],
        "Сначала — как этим пользоваться. Оператор открывает экран, вводит тему ролика в верхнее поле и нажимает «Создать прогон». Дальше всё делает система.",
    ),
    (
        "Результат и кнопки",
        ["__IMG__:data/ui_step2.png"],
        "Прокрутим вниз: виден результат по шагам и кнопки «Одобрить», «Отклонить», «Сгенерировать видео» и «Опубликовать» — так оператор управляет выпуском.",
    ),
    (
        "1. Идея",
        ["Сейчас: тему вводит оператор",
         "Варианты: вручную · контент-план · идеи из трендов"],
        "Первый шаг — идея. Сейчас тему вводит оператор. Можно подключить контент-план или генерацию идей из трендов.",
    ),
    (
        "2. Сценарий",
        ["Сейчас: LLM-агент на LangGraph",
         "Модели: OpenAI · Claude · DeepSeek · локально (Ollama)"],
        "Сценарий генерирует LLM-агент. Подходит любая модель — облачная или локальная.",
    ),
    (
        "3. Генерация",
        ["Сейчас: текст — LLM, визуал — из библиотеки",
         "Модели: Flux · SDXL · DALL·E · YandexART · Runway/Kling (видео)"],
        "Генерация: текст пишет LLM, визуал берётся из библиотеки. Можно подключить генерацию картинок или видео нейросетью.",
    ),
    (
        "4. Монтаж",
        ["Сейчас: сборка ffmpeg, озвучка piper",
         "Модели TTS: piper · Yandex SpeechKit · ElevenLabs"],
        "Монтаж: видео собирается на ffmpeg, озвучка — синтез речи. Голос можно взять офлайн или облачный нейро-голос.",
    ),
    (
        "5. Проверка",
        ["Сейчас: агент-судья qa + цикл доработки",
         "Модели: любая LLM (OpenAI/DeepSeek) или правила"],
        "Проверка: контент оценивает агент-судья, при замечаниях — доработка. Подходит любая LLM или простые правила.",
    ),
    (
        "6. Публикация",
        ["Сейчас: YouTube — рабочий; Telegram — готов; VK/устройства — расширение",
         "Варианты: официальные API или ферма устройств"],
        "Публикация: работают адаптеры площадок — YouTube уже публикует ролик. Можно официальные API или ферма устройств.",
    ),
    (
        "7. Анализ",
        ["Сейчас: метрики + база знаний (обучение)",
         "Варианты: YouTube Analytics · VK/TG stats · сквозная аналитика"],
        "Анализ: система собирает метрики и обучается на результатах. Метрики площадок или сквозная аналитика.",
    ),
    (
        "Программа показывает видео",
        ["__IMG__:data/ui_video.png"],
        "Готовое видео программа показывает прямо в карточке прогона — вот плеер с собранным роликом.",
    ),
    (
        "Результат — ролик от системы",
        ["Ролик собран и опубликован системой",
         "Дальше — фрагмент готового видео"],
        "А вот результат: ролик, который система собрала и опубликовала сама. Сейчас покажу фрагмент готового видео.",
    ),
    (
        "Технологии",
        ["Backend: Python, FastAPI, LangGraph, Pydantic",
         "Frontend: React, TypeScript, Vite",
         "Медиа: ffmpeg, Pillow, piper (TTS), numpy",
         "Данные: SQLite / PostgreSQL",
         "Интеграции: YouTube Data API (OAuth2), Telegram, device farm"],
        "И технологии. Backend на Python: FastAPI, мультиагентный граф на LangGraph, валидация через Pydantic. Frontend — React, TypeScript и Vite. Медиа — ffmpeg, Pillow и офлайн-синтез речи piper. Данные — SQLite или PostgreSQL. Интеграции — YouTube Data API с OAuth2, Telegram и ферма устройств.",
    ),
]


def _duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/fullcycle.mp4")
    parser.add_argument("--reel", default="data/reel.mp4", help="готовый ролик, который показать в конце")
    args = parser.parse_args()

    out = Path(args.out)
    work = out.parent / (out.stem + "_work")
    work.mkdir(parents=True, exist_ok=True)

    frames, audios, durations = [], [], []
    for i, (title, bullets, narration) in enumerate(SLIDES):
        frame = work / f"slide_{i}.png"
        if len(bullets) == 1 and bullets[0].startswith("__FULLIMG__:"):
            make_full_image_slide(title, bullets[0].split(":", 1)[1], i, len(SLIDES), frame)
        elif len(bullets) == 1 and bullets[0].startswith("__IMG__:"):
            make_image_slide(title, bullets[0].split(":", 1)[1], i, len(SLIDES), frame)
        else:
            make_slide(title, bullets, i, len(SLIDES), frame)
        frames.append(frame)

        wav = work / f"narr_{i}.wav"
        synthesize(narration, wav, settings)
        durations.append(max(_duration(wav) + 0.6, 2.0))
        audios.append(wav)

    voice = work / "voice.wav"
    _concat_wavs(audios, voice)
    voice_len = _duration(voice)
    music = work / "music.wav"
    generate_music(music, voice_len + 1.5)

    concat_file = work / "concat.txt"
    with concat_file.open("w", encoding="utf-8") as fh:
        for frame, dur in zip(frames, durations):
            fh.write(f"file '{frame.resolve().as_posix()}'\nduration {dur:.3f}\n")
        fh.write(f"file '{frames[-1].resolve().as_posix()}'\n")

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    explainer = work / "explainer.mp4"
    subprocess.run(
        [
            ff, "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-i", str(voice), "-i", str(music),
            "-filter_complex",
            f"[0:v]scale={W}:{H},format=yuv420p[vid];"
            f"[1:a]volume=1.0[v];[2:a]volume={settings.music_volume}[m];"
            "[v][m]amix=inputs=2:duration=first:dropout_transition=0[mix]",
            "-map", "[vid]", "-map", "[mix]",
            "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(explainer),
        ],
        check=True, capture_output=True,
    )

    reel = Path(args.reel)
    if reel.exists():
        result = work / "result.mp4"
        subprocess.run(
            [
                ff, "-y", "-i", str(reel),
                "-filter_complex",
                f"[0:v]scale=-2:{H},pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0f1117,format=yuv420p[v]",
                "-map", "[v]", "-map", "0:a",
                "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(result),
            ],
            check=True, capture_output=True,
        )
        subprocess.run(
            [
                ff, "-y", "-i", str(explainer), "-i", str(result),
                "-filter_complex", "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]",
                "-map", "[v]", "-map", "[a]",
                "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out),
            ],
            check=True, capture_output=True,
        )
    else:
        explainer.replace(out)

    print(f"Готово: {out.resolve()}  ({out.stat().st_size / 1024:.0f} КБ, {W}x{H})")
    print(f"Слайдов: {len(SLIDES)} · голос: {settings.tts_provider} · +ролик: {reel.exists()}")


if __name__ == "__main__":
    main()
