"""Нарезка длинного скриншота UI (data/ui_full.png) на кадры-этапы с подписями.

Используется для слайдов-объяснений «как работает программа».
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.video import _font

# (верх, низ, подпись) — вертикальные полосы, имитируют прокрутку страницы
BANDS = [
    (0, 900, "1. Введите тему ролика и нажмите «Создать прогон»"),
    (860, 1760, "2. Результат по шагам и кнопки «Одобрить / Отклонить»"),
    (1700, 2600, "3. Следующие прогоны и их статусы"),
]

CAP_H = 96


def main() -> None:
    src = Image.open("data/ui_full.png").convert("RGB")
    for i, (top, bottom, caption) in enumerate(BANDS):
        seg = src.crop((0, top, src.width, min(bottom, src.height)))
        bar = Image.new("RGB", (seg.width, CAP_H), (18, 22, 32))
        d = ImageDraw.Draw(bar)
        d.rectangle([0, 0, 8, CAP_H], fill=(108, 140, 255))
        d.text((34, 26), caption, font=_font(40), fill=(232, 236, 245))
        out = Image.new("RGB", (seg.width, seg.height + CAP_H))
        out.paste(seg, (0, 0))
        out.paste(bar, (0, seg.height))
        out.save(f"data/ui_step{i + 1}.png")
        print(f"data/ui_step{i + 1}.png", out.size)


if __name__ == "__main__":
    main()
