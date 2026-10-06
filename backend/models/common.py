"""
Общие схемы: ошибки, пагинация, базовые типы.
"""
from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Стандартный ответ при ошибке."""
    detail: str = Field(..., description="Описание ошибки")
    code: str | None = Field(None, description="Машинный код ошибки")


class Pagination(BaseModel):
    """Метаданные пагинации."""
    total: int = Field(..., description="Всего записей")
    limit: int = Field(..., description="Лимит на страницу")
    offset: int = Field(..., description="Смещение")


class PaginatedResponse(BaseModel, Generic[T]):
    """Универсальный ответ со списком и пагинацией."""
    items: list[T]
    pagination: Pagination