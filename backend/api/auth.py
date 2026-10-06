"""
Эндпоинты аутентификации.
"""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import text

from backend.auth.dependencies import (
    ACCESS_COOKIE, REFRESH_COOKIE,
    get_current_token, get_current_user,
)
from backend.auth.security import (
    create_access_token, create_refresh_token,
    decode_token, verify_password,
)
from backend.config import settings
from backend.db.postgres import tenant_session
from backend.models.auth import (
    LoginRequest, RefreshRequest, TokenResponse,
)
from backend.models.users import MeResponse, UserResponse


router = APIRouter(prefix="/auth", tags=["auth"])


# ─── Cookies ─────────────────────────────────────────────────
# secure=False — для локальной разработки по http.
# В продакшне ОБЯЗАТЕЛЬНО secure=True (только https).

COOKIE_COMMON = {
    "httponly": True,           # JS не может прочитать
    "secure": False,            # True в проде
    "samesite": "lax",          # защита от CSRF
}


def set_auth_cookies(response: Response, access: str, refresh: str):
    """Установить обе cookies."""
    response.set_cookie(
        ACCESS_COOKIE,
        access,
        max_age=settings.JWT_ACCESS_MINUTES * 60,
        path="/",
        **COOKIE_COMMON,
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        max_age=settings.JWT_REFRESH_DAYS * 24 * 3600,
        path="/auth/refresh",   # отправляется ТОЛЬКО на этот эндпоинт
        **COOKIE_COMMON,
    )


def clear_auth_cookies(response: Response):
    """Удалить обе cookies."""
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/auth/refresh")


# ─── Эндпоинты ───────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, response: Response):
    """
    Вход по email и паролю.
    Возвращает токены в JSON **и** устанавливает httpOnly cookies.
    """
    # Ищем пользователя по email во всех tenant'ах.
    # Для этого отключаем RLS (SET LOCAL не вызываем).
    from backend.db.postgres import get_session

    with get_session() as session:
        row = session.execute(
            text("""
                SELECT id, tenant_id, role, password_hash
                FROM users
                WHERE email = :email
                LIMIT 1
            """),
            {"email": payload.email},
        ).fetchone()

    if row is None:
        # Намеренно не говорим, что именно неверно (email или пароль)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    user_id, tenant_id, role, password_hash = row

    if not verify_password(payload.password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    access = create_access_token(user_id, tenant_id, role)
    refresh = create_refresh_token(user_id, tenant_id, role)

    set_auth_cookies(response, access, refresh)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_MINUTES * 60,
    )


@router.post("/logout")
async def logout(response: Response):
    """Выход — очищаем cookies."""
    clear_auth_cookies(response)
    return {"status": "ok"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest | None, response: Response):
    """
    Обновить access-токен по refresh-токену.
    Принимает refresh из cookie (PWA) или из тела (API-клиент).
    """
    from fastapi import Request
    # В FastAPI сложно одновременно читать cookie и body,
    # поэтому работаем через request напрямую (см. ниже)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Реализация через cookie — см. шаг 6 (опционально)",
    )


@router.get("/me", response_model=MeResponse)
async def me(user: UserResponse = Depends(get_current_user)):
    """
    Профиль текущего пользователя + список учеников (для учителя).
    """
    students = []
    if user.role in ("owner", "admin"):
        with tenant_session(user.tenant_id) as session:
            rows = session.execute(
                text("""
                    SELECT u.id, u.full_name
                    FROM users u
                    JOIN memberships m ON m.user_id = u.id
                    WHERE u.tenant_id = :t
                      AND u.role = 'student'
                    ORDER BY u.full_name
                """),
                {"t": user.tenant_id},
            ).fetchall()
            students = [{"id": r[0], "full_name": r[1]} for r in rows]

    return MeResponse(user=user, students=students)