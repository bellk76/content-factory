"""Генерация фоновой музыки (процедурно, без авторских прав).

Приятный «заводной» луп: прогрессия I–V–vi–IV (C–G–Am–F), мягкий пад,
арпеджио-плаки, лёгкий кик и хэт. Пишется в WAV (16-bit) заданной длительности,
чтобы использовать как подложку под озвучку.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 44100
# (название, аккордовые тона, басовая нота)
PROGRESSION = [
    ("C", [261.63, 329.63, 392.00], 130.81),
    ("G", [246.94, 293.66, 392.00], 98.00),
    ("Am", [261.63, 329.63, 440.00], 110.00),
    ("F", [220.00, 261.63, 349.23], 87.31),
]


def generate_music(path: Path, duration: float, bpm: int = 112) -> Path:
    beat = 60.0 / bpm
    eighth = beat / 2
    bar = 4 * beat
    total = int(SR * duration) + SR
    buf = np.zeros(total, dtype=np.float32)

    def add(start: float, sig: np.ndarray) -> None:
        i = int(start * SR)
        j = min(i + len(sig), total)
        if i < total and j > i:
            buf[i:j] += sig[: j - i]

    def envelope(t: np.ndarray, attack: float, release: float) -> np.ndarray:
        return np.clip(np.minimum(t / attack, 1) * np.minimum((t[-1] - t) / release, 1), 0, 1)

    def pad(freqs: list[float], dur: float, vol: float = 0.10) -> np.ndarray:
        t = np.linspace(0, dur, int(SR * dur), endpoint=False)
        sig = np.zeros_like(t)
        for f in freqs:
            sig += np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
        return (sig * envelope(t, 0.4, 0.6) * vol / len(freqs)).astype(np.float32)

    def pluck(freq: float, vol: float = 0.18) -> np.ndarray:
        t = np.linspace(0, 0.35, int(SR * 0.35), endpoint=False)
        return (np.sin(2 * np.pi * freq * t) * np.exp(-8 * t) * vol).astype(np.float32)

    def kick() -> np.ndarray:
        t = np.linspace(0, 0.25, int(SR * 0.25), endpoint=False)
        f = np.linspace(120, 45, len(t))
        phase = np.cumsum(2 * np.pi * f / SR)
        return (np.sin(phase) * np.exp(-18 * t) * 0.9).astype(np.float32)

    rng = np.random.default_rng(1)

    def hat() -> np.ndarray:
        t = np.linspace(0, 0.05, int(SR * 0.05), endpoint=False)
        return (rng.standard_normal(len(t)) * np.exp(-60 * t) * 0.14).astype(np.float32)

    nbars = int(np.ceil(duration / bar)) + 1
    for b in range(nbars):
        start = b * bar
        _, freqs, root = PROGRESSION[b % len(PROGRESSION)]
        add(start, pad(freqs, bar))
        add(start, pluck(root, 0.22))
        for k in range(8):
            tone = freqs[k % len(freqs)] * (2 if (k // len(freqs)) % 2 else 1)
            add(start + k * eighth, pluck(tone, 0.16))
        for k in range(4):
            add(start + k * beat, kick())
            add(start + k * beat + eighth, hat())

    peak = float(np.max(np.abs(buf))) or 1.0
    buf = buf / peak * 0.85
    fi = int(0.8 * SR)
    buf[:fi] *= np.linspace(0, 1, fi)
    fo = int(1.5 * SR)
    buf[-fo:] *= np.linspace(1, 0, fo)

    data = (np.clip(buf, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    return path
