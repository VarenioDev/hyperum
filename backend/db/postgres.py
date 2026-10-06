"""
Подключение к PostgreSQL.
Управляет engine, сессиями и RLS через SET LOCAL app.current_tenant.
"""
from contextlib import contextmanager
from typing import Iterator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from backend.config import settings


# ─── Engine ──────────────────────────────────────────────────
# pool_pre_ping — проверяет соединение перед выдачей из пула
# (важно, если БД перезапускается в Docker)

engine = create_engine(
    settings.DB_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


# ─── Базовые сессии ──────────────────────────────────────────

@contextmanager
def get_session() -> Iterator[Session]:
    """
    Обычная сессия без tenant-контекста.
    Используется для системных операций (миграции, admin).
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def tenant_session(tenant_id: str) -> Iterator[Session]:
    """
    Сессия с установленным app.current_tenant для RLS.
    Все запросы видят только данные своего tenant'а.

    SET LOCAL — важно: работает в пределах транзакции,
    при возврате соединения в пул переменная сбрасывается.
    """
    session = SessionLocal()
    try:
        # Открываем транзакцию и выставляем tenant для RLS
        session.begin()
        session.execute(
            text("SELECT set_config('app.current_tenant', :t, true)"),
            {"t": tenant_id},
        )
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ─── Проверка подключения ────────────────────────────────────

def ping() -> bool:
    """Проверка, что PostgreSQL жив."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def shutdown():
    """Закрыть пул соединений при остановке приложения."""
    engine.dispose()