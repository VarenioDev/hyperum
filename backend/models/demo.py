"""
Схемы для демонстрационного режима.
"""
from uuid import UUID
from pydantic import BaseModel, Field


class DemoStartRequest(BaseModel):
    """Запрос на запуск демо."""
    description: str = Field(
        ..., min_length=20, max_length=2000,
        description="Описание: что знаешь и что не знаешь"
    )


class DemoTask(BaseModel):
    """Задание в демо-тесте."""
    task_id: str
    code: str
    text: str
    position: int


class DemoStartResponse(BaseModel):
    """Ответ на старт демо."""
    session_id: str
    topic: str
    total_tasks: int
    reasoning: str = ""
    tasks: list[DemoTask]


class DemoResponseRequest(BaseModel):
    """Ответ ученика в демо."""
    session_id: UUID
    task_id: UUID
    answer: str = ""
    time_sec: int | None = None


class DemoResponseResult(BaseModel):
    """Результат ответа."""
    correct: bool
    expected: str | None = None
    new_mastery: float | None = None