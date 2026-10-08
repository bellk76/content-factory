"""Рендер видео из сценария: кадры (Pillow) + озвучка (TTS) + музыка (процедурная)
-> микс и склейка (ffmpeg) -> вертикальный mp4 1080x1920.

Используется и пайплайном (узел render), и CLI scripts/video_proof.py.
"""

from __future__ import annotations

import colorsys
import glob
import random
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from app.config import Settings, settings as default_settings
from app.services.music import generate_music
from app.services.tts import synthesize

W, H = 1080, 1920
FPS = 30


def _font(size: int) -> ImageFont.FreeTypeFont:
    for name in (
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ):
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()  # type: ignore[return-value]


def _rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    return tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h % 1.0, s, v))  # type: ignore[return-value]


def _darken_gradient(img: Image.Image) -> Image.Image:
    mask = Image.new("L", (1, H))
    for y in range(H):
        t = y / H
        if t < 0.34:
            a = int(225 * (0.34 - t) / 0.34)
        elif t > 0.70:
            a = int(235 * (t - 0.70) / 0.30)
        else:
            a = 0
        mask.putpixel((0, y), min(255, a))
    overlay = Image.new("RGBA", (W, H), (5, 7, 12, 0))
    overlay.putalpha(mask.resize((W, H)))
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def _rounded(img: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=radius, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def _make_photo_bg(photo: Path, out_path: Path) -> None:
    """Фон — размытая заливка; фото — чёткая «карточка» по центру (без апскейла)."""
    img = Image.open(photo).convert("RGB")

    # фон: cover + сильный блюр + затемнение (не мешает тексту)
    bg = ImageOps.fit(img, (W, H), method=Image.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(40))
    bg = Image.eval(bg, lambda c: int(c * 0.55)).convert("RGBA")
    bg = _darken_gradient(bg)

    # карточка: масштаб по ширине (обычно это уменьшение -> чётко), с полями
    card_w = W - 140
    card_h = int(img.height * card_w / img.width)
    max_h = int(H * 0.55)
    if card_h > max_h:
        card_h = max_h
    fg = img.resize((card_w, card_h), Image.LANCZOS)
    fg = fg.filter(ImageFilter.UnsharpMask(radius=2, percent=90, threshold=3))
    fg = _rounded(fg, 30)

    x = (W - card_w) // 2
    y = int(H * 0.60 - card_h / 2)

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [x - 8, y - 8, x + card_w + 8, y + card_h + 8], radius=38, fill=(0, 0, 0, 160)
    )
    bg = Image.alpha_composite(bg, shadow.filter(ImageFilter.GaussianBlur(20)))
    bg.alpha_composite(fg, (x, y))
    bg = Image.alpha_composite(bg, Image.new("RGBA", (W, H), (18, 28, 66, 26)))
    bg.convert("RGB").save(out_path)


def _make_art_bg(out_path: Path, index: int) -> None:
    rnd = random.Random(1000 + index)
    hue = (0.60 + 0.07 * index) % 1.0
    accent = _rgb(hue + 0.03, 0.55, 0.98)
    top, bot = _rgb(hue, 0.55, 0.34), _rgb(hue, 0.7, 0.07)
    grad = Image.new("RGB", (1, H))
    for y in range(H):
        t = y / H
        grad.putpixel((0, y), tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    bg = grad.resize((W, H)).convert("RGBA")
    bok = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bok)
    for _ in range(30):
        r = rnd.randint(18, 90)
        x, y = rnd.randint(0, W), rnd.randint(int(H * 0.15), int(H * 0.85))
        bd.ellipse([x - r, y - r, x + r, y + r], fill=_rgb(hue + 0.5, 0.4, 0.95) + (rnd.randint(16, 42),))
    bg = Image.alpha_composite(bg, bok.filter(ImageFilter.GaussianBlur(20)))
    d = ImageDraw.Draw(bg, "RGBA")
    fx0, fx1, fy0, fy1 = int(W * 0.30), int(W * 0.72), int(H * 0.45), int(H * 0.90)
    d.rounded_rectangle([fx0 - 20, fy0 - 18, fx1 + 20, fy1], radius=28, fill=_rgb(hue, 0.45, 0.10))
    d.rounded_rectangle([fx0, fy0, fx1, fy1], radius=16, fill=_rgb(hue, 0.28, 0.44), outline=accent + (200,), width=4)
    hx, hy = fx1 - 76, (fy0 + fy1) // 2
    d.ellipse([hx - 15, hy - 15, hx + 15, hy + 15], fill=(224, 190, 116, 255))
    bg.convert("RGB").save(out_path)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        candidate = (cur + " " + word).strip()
        if draw.textlength(candidate, font=font) < W - 200:
            cur = candidate
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _block(base: Image.Image, lines: list[str], font: ImageFont.FreeTypeFont, y: int,
           gap: int, fill, box=(10, 12, 18, 165)) -> None:
    d = ImageDraw.Draw(base, "RGBA")
    widths = [d.textlength(ln, font=font) for ln in lines]
    bw = max(widths) + 140
    bh = len(lines) * gap + 72
    x0 = (W - bw) / 2
    d.rounded_rectangle([x0, y, x0 + bw, y + bh], radius=28, fill=box)
    yy = y + 36
    for ln, w in zip(lines, widths):
        d.text(((W - w) / 2, yy), ln, font=font, fill=fill)
        yy += gap


def _make_frames(topic: str, scenes: list[str], out_dir: Path, assets_dir: Path) -> list[Path]:
    photos = sorted(glob.glob(str(assets_dir / "*.jpg"))) if assets_dir.exists() else []
    f_head, f_body, f_meta = _font(50), _font(66), _font(34)
    frames = []
    for i, body in enumerate(scenes):
        bg_path = out_dir / f"bg_{i}.png"
        if photos:
            _make_photo_bg(Path(photos[i % len(photos)]), bg_path)
        else:
            _make_art_bg(bg_path, i)
        img = Image.open(bg_path).convert("RGBA")
        d = ImageDraw.Draw(img, "RGBA")
        _block(img, _wrap(d, topic, f_head), f_head, 140, 60, (200, 210, 235, 255))
        _block(img, _wrap(d, body, f_body), f_body, int(H * 0.15), 84, (240, 242, 247, 255))
        ImageDraw.Draw(img).text((60, H - 120), f"content-factory · кадр {i + 1}/{len(scenes)}",
                                 font=f_meta, fill=(150, 175, 255))
        frame = out_dir / f"frame_{i}.png"
        img.convert("RGB").save(frame)
        frames.append(frame)
    return frames


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


def render_video(
    topic: str,
    scenes: list[str],
    cta: str = "",
    out_path: Path | str = "data/reel.mp4",
    config: Settings | None = None,
) -> Path:
    cfg = config or default_settings
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    scenes = scenes or [topic]

    # изолированный временный рабочий каталог (безопасно при параллельных рендерах)
    work = Path(tempfile.mkdtemp(prefix="cf_render_", dir=str(out.parent)))
    try:
        frames = _make_frames(topic, scenes, work, Path(cfg.assets_dir))
        audios, durations = [], []
        for i, body in enumerate(scenes):
            wav = work / f"voice_{i}.wav"
            synthesize(f"{body}.", wav, cfg)
            durations.append(max(_wav_duration(wav) + 0.5, 1.6))
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
                f"[1:a]volume=1.0[v];[2:a]volume={cfg.music_volume}[m];"
                "[v][m]amix=inputs=2:duration=first:dropout_transition=0[mix]",
                "-map", "[vid]", "-map", "[mix]",
                "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-shortest", str(out),
            ],
            check=True, capture_output=True,
        )
        return out
    finally:
        shutil.rmtree(work, ignore_errors=True)
