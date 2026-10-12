"""
Схемы рекомендаций.
"""
from uuid import UUID
from pydantic import BaseModel, Field


class RecommendedTask(BaseModel):
    """Задание, рекомендованное ученику."""
    task_id: UUID
    code: str
    text: str
    type: str = "text"
    options: dict | None = None
    difficulty: float | None = None


class NextTaskRecommendation(BaseModel):
    """Рекомендация «следующий шаг»."""
    skill_id: str
    skill_name: str
    skill_mastery: float = Field(..., ge=0.0, le=1.0)
    reason: str
    task: RecommendedTask