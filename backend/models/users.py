"""
Схемы пользователей.
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, EmailStr


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