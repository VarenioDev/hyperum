"""
Безопасность: хеширование паролей и работа с JWT.
Используется bcrypt напрямую (без passlib).
"""
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from backend.config import settings
from backend.models.auth import TokenPayload


# ─── Пароли ──────────────────────────────────────────────────

def _prehash(password: str) -> bytes:
    """
    Предварительное хеширование SHA-256 для обхода ограничения bcrypt в 72 байта.
    Возвращает 32 байта.
    """
    return hashlib.sha256(password.encode("utf-8")).digest()


def hash_password(password: str) -> str:
    """Хешировать пароль: SHA-256 → bcrypt → строка."""
    prehashed = _prehash(password)
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(prehashed, salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Проверить пароль против хеша."""
    if not hashed:
        return False
    try:
        prehashed = _prehash(password)
        return bcrypt.checkpw(prehashed, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ─── JWT ─────────────────────────────────────────────────────

def _create_token(
    user_id: str,
    tenant_id: str,
    role: str,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    """Внутренняя функция создания JWT."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_access_token(user_id: UUID | str, tenant_id: str, role: str) -> str:
    """Access-токен на 1 час."""
    return _create_token(
        str(user_id), tenant_id, role, "access",
        timedelta(minutes=settings.JWT_ACCESS_MINUTES),
    )


def create_refresh_token(user_id: UUID | str, tenant_id: str, role: str) -> str:
    """Refresh-токен на 30 дней."""
    return _create_token(
        str(user_id), tenant_id, role, "refresh",
        timedelta(days=settings.JWT_REFRESH_DAYS),
    )


def decode_token(token: str) -> TokenPayload | None:
    """Проверить JWT и вернуть payload."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return TokenPayload(**payload)
    except (JWTError, ValueError):
        return None