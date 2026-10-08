"""Pydantic-схемы structured output для каждого агента.

Каждый агент обязан вернуть валидируемый JSON по своей схеме — это ключевое
инженерное требование: результат шага проверяем, а не «просто текст».
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ResearchResult(BaseModel):
    topic: str = Field(description="Тема ролика")
    audience: str = Field(description="Целевая аудитория")
    hooks: list[str] = Field(description="Зацепки для начала ролика (3-5)")
    facts: list[str] = Field(description="Факты/аргументы по теме (3-5)")
    angles: list[str] = Field(description="Ракурсы подачи")


class ScriptScene(BaseModel):
    t: float = Field(description="Таймкод сцены, сек")
    text: str = Field(description="Текст/озвучка сцены")
    visual: str = Field(description="Что в кадре")


class ScriptResult(BaseModel):
    title: str
    hook: str
    scenes: list[ScriptScene]
    cta: str = Field(description="Призыв к действию")
    duration_sec: int


class ContentResult(BaseModel):
    description: str = Field(description="Описание под публикацией")
    hashtags: list[str]
    captions: list[str] = Field(description="Варианты заголовка/подписи")


class MontageShot(BaseModel):
    t: float = Field(description="Таймкод, сек")
    scene: str = Field(description="Сцена/кадр из сценария")
    asset: str = Field(description="Что использовать: b-roll, графика, титр, крупный план")
    transition: str = Field(description="Переход к следующему кадру")


class MontageResult(BaseModel):
    timeline: list[MontageShot]
    music: str = Field(description="Музыка/тон")
    captions: bool = Field(description="Нужны ли субтитры")
    export: str = Field(description="Формат и параметры экспорта (например, 1080x1920, 30fps)")


class QAIssue(BaseModel):
    severity: str = Field(description="low | medium | high")
    message: str
    fix: str


class QAReport(BaseModel):
    passed: bool
    score: float = Field(description="Оценка 0-100")
    issues: list[QAIssue] = Field(default_factory=list)


class PublishResult(BaseModel):
    platform: str
    status: str = Field(description="published | dry_run | queued | error")
    post_id: Optional[str] = None
    url: Optional[str] = None


class AnalyticsResult(BaseModel):
    post_id: str
    views: int
    likes: int
    comments: int
    ctr: float
    summary: str
