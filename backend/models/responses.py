"""
Схемы ответов учеников и mastery.
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class ResponseCreate(BaseModel):
    task_id: UUID
    assignment_id: UUID | None = Field(None, description="ID текущего теста")
    answer: str = Field("", description="Ответ ученика")
    time_sec: int | None = Field(None, ge=0)
    skipped: bool = Field(False, description="Задание пропущено")
    surrendered: bool = Field(False, description="Ученик сдался (финально)")


class ResponseResult(BaseModel):
    """Результат проверки ответа."""
    correct: bool
    expected: str | None = Field(None, description="Правильный ответ")
    explanation: str | None = Field(None, description="Пояснение")
    new_mastery: float | None = Field(None, ge=0.0, le=1.0)
    skipped: bool = False


class ResponseResponse(BaseModel):
    id: UUID
    task_id: UUID
    code: str | None = None
    task_text: str | None = None
    expected: str | None = None
    answer: str
    correct: bool | None
    skipped: bool = False
    time_sec: int | None
    created_at: datetime
    assignment_title: str | None = None
    skill_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MasteryItem(BaseModel):
    """Mastery по одному навыку."""
    skill_id: str
    skill_name: str
    mastery: float = Field(..., ge=0.0, le=1.0)
    attempts: int
    correct: int
    updated_at: datetime | None = None


class StudentMastery(BaseModel):
    """Полный профиль mastery ученика."""
    student_id: UUID
    full_name: str
    skills: list[MasteryItem]


class ClassMasteryItem(BaseModel):
    """Mastery класса по навыку."""
    skill_id: str
    skill_name: str
    avg_mastery: float
    student_count: int

class ClassMastery(BaseModel):
    """Полный агрегат класса."""
    class_name: str
    skills: list[ClassMasteryItem]

class AssignmentProgress(BaseModel):
    """Прогресс по назначению для учителя."""
    assignment_id: UUID
    title: str
    total_students: int
    completed_students: int
    total_attempts: int
    correct_rate: float


class TaskStat(BaseModel):
    """Статистика по заданию."""
    task_id: UUID
    code: str
    attempts: int
    correct: int
    success_rate: float
    skill_id: str | None = None