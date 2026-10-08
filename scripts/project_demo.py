"""Ролик-презентация проекта: что это, зачем и как работает (со слайдами и озвучкой).

Использует те же сервисы, что и конвейер: TTS (piper/sapi), процедурную музыку,
сборку через ffmpeg. Результат: вертикальный mp4 1080x1920.

Запуск:
    python scripts/project_demo.py --out data/project_demo.mp4
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import wave
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.services.music import generate_music
from app.services.tts import synthesize
from app.services.video import _font, _rgb, _rounded

W, H = 1920, 1080  # горизонтальный ролик (16:9)

FPS = 30

SLIDES = [
    (
        "content-factory — веб-приложение",
        ["Мультиагентная система производства видео"],
        "Это content-factory — веб-приложение для автоматического производства видео. Из одной темы система делает готовый ролик и публикует его на площадки.",
    ),
    (
        "Шаг 1: создаём прогон",
        ["__IMG__:data/ui_step1.png"],
        "Начнём с того, как это выглядит для оператора. Он открывает экран, вводит тему ролика в верхнее поле, при желании указывает бренд и нажимает кнопку «Создать прогон». Дальше всё делает система.",
    ),
    (
        "Шаг 2: результат и решение",
        ["__IMG__:data/ui_step2.png"],
        "Прокрутим вниз. Здесь виден результат по каждому шагу: готовый сценарий, план монтажа, оценка качества и список публикаций на площадках. Ниже — кнопки «Одобрить» и «Отклонить»: так оператор управляет выпуском или отправляет на доработку.",
    ),
    (
        "Шаг 3: следующие прогоны",
        ["__IMG__:data/ui_step3.png"],
        "И дальше — следующие прогоны с их статусами. У каждого ролика видно, что проверено и где остаются пробелы, — это и есть рабочий поток оператора.",
    ),
    (
        "Проблема",
        ["Контент руками — медленно и дорого",
         "Много рутины: сценарии, монтаж, публикация",
         "Тяжело масштабировать на десятки аккаунтов"],
        "Производить контент вручную долго и дорого: сценарии, озвучка, монтаж и публикация съедают время, а масштабировать это на десятки аккаунтов почти невозможно.",
    ),
    (
        "Идея",
        ["Одна тема на входе",
         "Готовый вертикальный ролик на выходе",
         "Публикация — автоматически"],
        "Идея простая: на входе одна тема, на выходе — готовый вертикальный ролик, уже опубликованный на площадки.",
    ),
    (
        "Как это работает",
        ["research — ресёрч темы и аудитории",
         "script — сценарий со сценами и CTA",
         "generate — тексты и описания",
         "montage — план монтажа",
         "qa — контроль качества",
         "render — сборка видео: голос, субтитры, музыка",
         "publish — публикация на площадки",
         "analytics — метрики и обучение"],
        "Работает конвейер из AI-агентов: ресёрч, сценарий, генерация текстов, план монтажа, контроль качества, рендер видео, публикация и аналитика.",
    ),
    (
        "Ключевые принципы",
        ["Строгий структурированный вывод на каждом шаге",
         "Цикл доработки при провале проверки",
         "Единая база знаний",
         "Обратная связь: метрики меняют следующие ролики"],
        "Ключевое: строгий структурированный вывод на каждом шаге, цикл доработки при провале проверки, единая база знаний и обратная связь — метрики улучшают следующие ролики.",
    ),
    (
        "Архитектура и интеграции",
        ["Мультиагентный граф и оркестрация",
         "Интеграции: LLM, внешние API, база данных",
         "Адаптеры площадок и устройств",
         "Единая база знаний и метрики"],
        "Архитектурно это мультиагентный граф с оркестрацией, который интегрирует LLM, внешние API и базу данных, а также адаптеры площадок и устройств — всё замкнуто на единую базу знаний и метрики.",
    ),
    (
        "Публикация и площадки",
        ["YouTube — рабочий адаптер (OAuth2)",
         "Telegram, VK — через API",
         "Площадки без API — ферма устройств",
         "Очередь задач, ретраи, расписание"],
        "Публикация сделана адаптерами площадок: YouTube работает через OAuth2, Telegram и VK — через их API, а для площадок без API предусмотрена ферма устройств — очередь задач с воркером, ретраями и расписанием.",
    ),
    (
        "Голос",
        ["Сейчас — офлайн-синтез (Piper)",
         "Цель — живой, человеческий голос",
         "Нужен ключ: Yandex SpeechKit или ElevenLabs",
         "Переключается переменной TTS_PROVIDER"],
        "Сейчас озвучка — офлайн-синтез. Цель — живой, человеческий голос. Для этого достаточно подключить нейро-TTS, например Yandex SpeechKit или ElevenLabs: нужен API-ключ, а переключение делается одной переменной окружения.",
    ),
    (
        "Результат",
        ["Ролик собран и опубликован системой",
         "youtu.be/jVesRSVvi2E",
         "Одна команда: тема → видео → публикация"],
        "Результат уже можно посмотреть: ролик собран и опубликован самой системой. Одна команда — тема, видео, публикация.",
    ),
    (
        "Технологии",
        ["Backend: Python, FastAPI, LangGraph, Pydantic",
         "Frontend: React, TypeScript, Vite",
         "Медиа: ffmpeg, Pillow, piper (TTS), numpy",
         "Данные: SQLite / PostgreSQL",
         "Интеграции: YouTube Data API (OAuth2), Telegram, device farm",
         "Инфраструктура: Docker, GitHub Actions (CI), pytest"],
        "И в завершение — о технологиях. Backend на Python: FastAPI, мультиагентный граф на LangGraph, валидация через Pydantic. Frontend — React, TypeScript и Vite. Медиа — ffmpeg, Pillow и офлайн-синтез речи piper. Данные — SQLite или PostgreSQL. Интеграции — YouTube Data API с OAuth2, Telegram и ферма устройств. Инфраструктура — Docker, CI на GitHub Actions и тесты на pytest.",
    ),
]


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        candidate = (cur + " " + word).strip()
        if draw.textlength(candidate, font=font) < max_width:
            cur = candidate
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _ui_background() -> Image.Image:
    """Размытый затемнённый скриншот интерфейса как фон слайда."""
    shot = Path("data/ui_shot.png")
    if shot.exists():
        bg = ImageOps.fit(Image.open(shot).convert("RGB"), (W, H), method=Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(44))
        return Image.eval(bg, lambda c: int(c * 0.42)).convert("RGBA")
    return Image.new("RGB", (W, H), (18, 22, 32)).convert("RGBA")


def make_slide(title: str, bullets: list[str], index: int, total: int, path: Path) -> None:
    img = _ui_background()
    d = ImageDraw.Draw(img, "RGBA")

    f_t, f_b, f_m = _font(96), _font(54), _font(38)
    y = 150
    for line in _wrap(d, title, f_t, W - 160):
        d.text(((W - d.textlength(line, font=f_t)) / 2, y), line, font=f_t, fill=(240, 242, 247, 255))
        y += 94

    lines: list[str] = []
    for b in bullets:
        wrapped = _wrap(d, b, f_b, W - 320)
        for i, ln in enumerate(wrapped):
            lines.append(("•  " if i == 0 else "    ") + ln)

    gap, pad = 74, 56
    block_h = len(lines) * gap + pad * 2
    block_y = max(y + 40, int(H * 0.5 - block_h / 2))
    d.rounded_rectangle([90, block_y, W - 90, block_y + block_h], radius=32, fill=(10, 12, 18, 165))
    ty = block_y + pad
    for ln in lines:
        d.text((150, ty), ln, font=f_b, fill=(235, 238, 244, 255))
        ty += gap

    d.text((60, H - 110), f"content-factory · демо · {index + 1}/{total}", font=f_m, fill=(150, 175, 255, 255))
    img.convert("RGB").save(path)


def make_image_slide(title: str, image_path: str, index: int, total: int, path: Path) -> None:
    hue = (0.60 + 0.06 * index) % 1.0
    accent = _rgb(hue + 0.05, 0.6, 0.98)
    shot = Image.open(image_path).convert("RGB")

    # фон — размытый затемнённый тот же экран
    bg = ImageOps.fit(shot, (W, H), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(42))
    bg = Image.eval(bg, lambda c: int(c * 0.45)).convert("RGBA")
    d = ImageDraw.Draw(bg, "RGBA")

    f_t, f_m = _font(84), _font(38)
    y = 110
    for line in _wrap(d, title, f_t, W - 160):
        d.text(((W - d.textlength(line, font=f_t)) / 2, y), line, font=f_t, fill=(240, 242, 247, 255))
        y += 84
    top_of_card = y + 20
    bottom_limit = H - 150

    card_w = W - 90
    card_h = int(shot.height * card_w / shot.width)
    avail = bottom_limit - top_of_card
    if card_h > avail:
        shot = shot.crop((0, 0, shot.width, int(shot.width * avail / card_w)))
        card_h = avail
    card = shot.resize((card_w, card_h), Image.LANCZOS).filter(
        ImageFilter.UnsharpMask(radius=2, percent=70, threshold=3)
    )
    card = _rounded(card, 22)

    x = (W - card_w) // 2
    yy = top_of_card + max(0, (avail - card_h) // 2)  # центр в остатке

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [x - 8, yy - 8, x + card_w + 8, yy + card_h + 8], radius=28, fill=(0, 0, 0, 185)
    )
    bg = Image.alpha_composite(bg, shadow.filter(ImageFilter.GaussianBlur(20)))
    bg.alpha_composite(card, (x, yy))

    ImageDraw.Draw(bg).text((60, H - 66), f"content-factory · демо · {index + 1}/{total}",
                            font=f_m, fill=(150, 175, 255, 255))
    bg.convert("RGB").save(path)


def make_full_image_slide(title: str, image_path: str, index: int, total: int, path: Path) -> None:
    """Полноэкранный скриншот с заголовком сверху."""
    shot = Image.open(image_path).convert("RGB")
    img = ImageOps.fit(shot, (W, H), method=Image.LANCZOS).convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle([0, 0, W, 230], fill=(6, 8, 14, 205))
    img = Image.alpha_composite(img, overlay)
    d = ImageDraw.Draw(img)
    d.text((70, 70), title, font=_font(72), fill=(240, 242, 247, 255))
    d.text((70, H - 70), f"content-factory · демо · {index + 1}/{total}", font=_font(34), fill=(160, 180, 255, 255))
    img.convert("RGB").save(path)


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def _concat_wavs(paths: list[Path], out: Path) -> None:
    with wave.open(str(paths[0]), "rb") as first:
        params = first.getparams()
    with wave.open(str(out), "wb") as dst:
        dst.setparams(params)
        for p in paths:
            with wave.open(str(p), "rb") as src:
                dst.writeframes(src.readframes(src.getnframes()))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/project_demo.mp4")
    args = parser.parse_args()

    out = Path(args.out)
    work = out.parent / (out.stem + "_work")
    work.mkdir(parents=True, exist_ok=True)

    frames, audios, durations = [], [], []
    for i, (title, bullets, narration) in enumerate(SLIDES):
        frame = work / f"slide_{i}.png"
        if len(bullets) == 1 and bullets[0].startswith("__IMG__:"):
            make_image_slide(title, bullets[0].split(":", 1)[1], i, len(SLIDES), frame)
        else:
            make_slide(title, bullets, i, len(SLIDES), frame)
        frames.append(frame)

        wav = work / f"narr_{i}.wav"
        synthesize(narration, wav, settings)
        durations.append(max(_wav_duration(wav) + 0.6, 2.0))
        audios.append(wav)

    voice = work / "voice.wav"
    _concat_wavs(audios, voice)
    voice_len = _wav_duration(voice)
    music = work / "music.wav"
    generate_music(music, voice_len + 1.5)

    concat_file = work / "concat.txt"
    with concat_file.open("w", encoding="utf-8") as fh:
        for frame, dur in zip(frames, durations):
            fh.write(f"file '{frame.resolve().as_posix()}'\nduration {dur:.3f}\n")
        fh.write(f"file '{frames[-1].resolve().as_posix()}'\n")

    subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(), "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-i", str(voice), "-i", str(music),
            "-filter_complex",
            f"[0:v]scale={W}:{H},format=yuv420p[vid];"
            f"[1:a]volume=1.0[v];[2:a]volume={settings.music_volume}[m];"
            "[v][m]amix=inputs=2:duration=first:dropout_transition=0[mix]",
            "-map", "[vid]", "-map", "[mix]",
            "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(out),
        ],
        check=True, capture_output=True,
    )
    print(f"Готово: {out.resolve()}  ({out.stat().st_size / 1024:.0f} КБ, ~{voice_len:.1f} c, {W}x{H})")
    print(f"Слайдов: {len(SLIDES)} · голос: {settings.tts_provider}")


if __name__ == "__main__":
    main()
