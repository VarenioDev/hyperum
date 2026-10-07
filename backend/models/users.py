"""
Схемы пользователей.
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator


class UserBase(BaseModel):
    """Общие поля пользователя."""
    full_name: str = Field(..., min_length=2, description="ФИО")
    email: EmailStr | None = None


class UserResponse(UserBase):
    """Полный профиль пользователя (отдаётся из API)."""
    id: UUID
    tenant_id: str
    role: str = Field(..., description="owner / student / admin")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentBrief(BaseModel):
    """Краткая карточка ученика (для списков)."""
    id: UUID
    full_name: str

    model_config = ConfigDict(from_attributes=True)


class MeResponse(BaseModel):
    """Профиль текущего пользователя (включая учеников для учителя)."""
    user: UserResponse
    students: list[StudentBrief] = Field(
        default_factory=list,
        description="Ученики (для учителя/репетитора)"
    )


class StudentCreate(BaseModel):
    """Создание ученика (учителем)."""
    full_name: str = Field(..., min_length=2)
    email: EmailStr | None = None
    group_id: UUID | None = Field(None, description="Класс/группа")

class StudentUpdate(BaseModel):
    """Обновление данных ученика учителем."""
    full_name: str = Field(..., min_length=5, max_length=100)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        import re
        v = v.strip()
        if not re.match(r"^[А-Яа-яЁё\s\-]+$", v):
            raise ValueError("ФИО должно содержать только русские буквы, пробелы и дефисы")
        parts = [p for p in re.split(r"\s+", v) if p]
        if len(parts) < 2:
            raise ValueError("Укажите фамилию и имя")
        return " ".join(p.capitalize() for p in parts)