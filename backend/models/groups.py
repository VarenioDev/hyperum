"""
Схемы для работы с классами и регистрацией учеников.
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, EmailStr


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
    """Регистрация ученика по инвайт-коду."""
    code: str = Field(..., min_length=4, max_length=10)
    full_name: str = Field(..., min_length=2)
    email: EmailStr
    password: str = Field(..., min_length=6)


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