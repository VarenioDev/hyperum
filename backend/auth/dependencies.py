"""
FastAPI-зависимости для аутентификации.
"""
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.auth.security import decode_token
from backend.db.postgres import tenant_session
from backend.models.auth import TokenPayload
from backend.models.users import UserResponse


# Имя cookies
ACCESS_COOKIE = "hyperum_access"
REFRESH_COOKIE = "hyperum_refresh"


def extract_token(request: Request) -> str | None:
    """
    Достать токен из запроса.
    Приоритет:
    1. httpOnly cookie (для PWA)
    2. Authorization: Bearer (для API-интеграций)
    """
    # 1. Cookie
    token = request.cookies.get(ACCESS_COOKIE)
    if token:
        return token

    # 2. Authorization header
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()

    return None


def get_current_token(request: Request) -> TokenPayload:
    """
    Достать и проверить access-токен.
    Бросает 401, если токена нет или он невалидный.
    """
    token = extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен не предоставлен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или истёкший токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ожидался access-токен",
        )

    return payload


def get_current_user(
    token: TokenPayload = Depends(get_current_token),
) -> UserResponse:
    """
    Загрузить профиль текущего пользователя из БД.
    Автоматически устанавливает RLS-контекст по tenant_id из токена.
    """
    with tenant_session(token.tenant_id) as session:
        row = session.execute(
            text("""
                SELECT id, tenant_id, role, full_name, email, created_at
                FROM users
                WHERE id = :uid
            """),
            {"uid": token.sub},
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )

    return UserResponse(
        id=row[0],
        tenant_id=row[1],
        role=row[2],
        full_name=row[3],
        email=row[4],
        created_at=row[5],
    )


def require_role(*allowed: str):
    """
    Фабрика зависимостей для проверки роли.

    Использование:
        @router.get("/teacher-only")
        def endpoint(user = Depends(require_role("owner", "admin"))):
            ...
    """
    def checker(user: UserResponse = Depends(get_current_user)) -> UserResponse:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Требуется роль: {' или '.join(allowed)}",
            )
        return user

    return checker


# Удобные алиасы
require_teacher = require_role("owner", "admin")
require_student = require_role("student")