"""
Схемы заданий и их разметки.
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class TaskLabel(BaseModel):
    """Разметка задания по навыку."""
    skill_id: str = Field(..., description="ID навыка")
    difficulty: float = Field(..., ge=0.0, le=1.0, description="Сложность 0..1")
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    model: str | None = Field(None, description="Модель, сделавшая разметку")
    reasoning: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TaskBase(BaseModel):
    """Базовые поля задания."""
    code: str = Field(..., description="Человекочитаемый код task_XXX")
    text: str = Field(..., min_length=1, description="Текст задания")
    type: str = Field("text", description="Тип: text / single_choice / multi_choice")
    answer: str | None = None
    options: dict | None = None


class TaskResponse(TaskBase):
    """Полное задание с разметкой."""
    id: UUID
    visibility: str = Field("shared", description="shared / tenant / private")
    labels: list[TaskLabel] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TaskBrief(BaseModel):
    """Краткая карточка задания."""
    id: UUID
    code: str
    text: str
    difficulty: float | None = Field(None, ge=0.0, le=1.0)
    skill_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    """Создание задания."""
    code: str = Field(..., pattern=r"^task_\d+$", description="Формат: task_XXX")
    text: str = Field(..., min_length=1)
    type: str = Field("text")
    answer: str | None = None
    options: dict | None = None
    skill_id: str | None = None
    difficulty: float | None = Field(None, ge=0.0, le=1.0)