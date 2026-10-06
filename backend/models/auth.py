"""
Схемы аутентификации.
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr


class LoginRequest(BaseModel):
    """Запрос на вход."""
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., min_length=6, description="Пароль")


class TokenResponse(BaseModel):
    """Ответ с токенами."""
    access_token: str = Field(..., description="JWT access-токен")
    refresh_token: str = Field(..., description="JWT refresh-токен")
    token_type: str = Field("bearer", description="Тип токена")
    expires_in: int = Field(..., description="Время жизни access-токена в секундах")


class TokenPayload(BaseModel):
    """Полезная нагрузка JWT (используется внутри при проверке)."""
    sub: str = Field(..., description="UUID пользователя")
    tenant_id: str = Field(..., description="ID организации")
    role: str = Field(..., description="Роль: owner / student / admin")
    exp: int = Field(..., description="Время истечения (unix timestamp)")
    type: str = Field(..., description="Тип токена: access / refresh")


class RefreshRequest(BaseModel):
    """Запрос на обновление access-токена."""
    refresh_token: str = Field(...)