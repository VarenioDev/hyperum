"""
Схемы для работы с классами и регистрацией учеников.
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, EmailStr
import re
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator


# ─── Создание класса ────────────────────────────────────────

class GroupCreate(BaseModel):
    """Создание нового класса учителем."""
    name: str = Field(..., min_length=2, max_length=50,
                      description="Название: 10А, 11Б и т.п.")
    subject: str = Field("informatics", max_length=30)
    kind: str = Field("class", pattern="^(class|tutor_group|one_on_one)$")


class GroupResponse(BaseModel):
    """Информация о классе."""
    id: UUID
    name: str
    subject: str
    kind: str
    invite_code: str | None = None
    students_count: int = 0
    pending_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentBrief(BaseModel):
    """Краткая карточка ученика в классе."""
    id: UUID
    full_name: str
    email: str | None = None
    status: str = "active"
    mastery_avg: float | None = None
    joined_at: datetime | None = None
    active_assignments: int = 0
    last_completed_title: str | None = None
    last_completed_score: str | None = None
    days_since_activity: int | None = None


class GroupDetail(GroupResponse):
    """Детали класса с учениками."""
    students: list[StudentBrief] = Field(default_factory=list)


# ─── Публичная информация по коду ───────────────────────────

class GroupByCode(BaseModel):
    """Что видит ученик, вводя инвайт-код."""
    name: str
    subject: str
    teacher_name: str


# ─── Регистрация ученика по коду ────────────────────────────

class JoinRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=10)
    full_name: str = Field(..., min_length=5, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        v = v.strip()

        # Только кириллица, пробелы и дефисы
        if not re.match(r"^[А-Яа-яЁё\s\-]+$", v):
            raise ValueError("ФИО должно содержать только русские буквы, пробелы и дефисы")

        # Минимум 2 слова
        parts = [p for p in re.split(r"\s+", v) if p]
        if len(parts) < 2:
            raise ValueError("Укажите фамилию и имя")

        # Каждое слово — минимум 2 буквы
        for part in parts:
            if len(part) < 2:
                raise ValueError("Каждая часть ФИО должна содержать минимум 2 буквы")

        # Первая буква каждого слова — заглавная (не строго, но нормализуем)
        normalized = " ".join(p.capitalize() for p in parts)
        return normalized


class JoinResponse(BaseModel):
    """Ответ после регистрации."""
    status: str = "pending"
    message: str
    group_name: str


# ─── Подтверждение / отклонение ─────────────────────────────

class ApproveResponse(BaseModel):
    """Результат подтверждения."""
    student_id: UUID
    status: str
    message: str

class GroupUpdate(BaseModel):
    """Обновление класса."""
    name: str = Field(..., min_length=2, max_length=50)
    subject: str | None = None