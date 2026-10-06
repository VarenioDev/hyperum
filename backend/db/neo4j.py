"""
Подключение к Neo4j.
Управляет driver'ом и сессиями.
"""
from contextlib import contextmanager
from typing import Iterator
from neo4j import GraphDatabase, Driver, Session

from backend.config import settings


# ─── Driver ──────────────────────────────────────────────────
# Создаётся один раз на всё приложение. Потокобезопасен.

_driver: Driver | None = None


def get_driver() -> Driver:
    """Ленивая инициализация driver'а."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
    return _driver


@contextmanager
def neo4j_session() -> Iterator[Session]:
    """Сессия для запросов к Neo4j."""
    driver = get_driver()
    session = driver.session()
    try:
        yield session
    finally:
        session.close()


def ping() -> bool:
    """Проверка, что Neo4j жив."""
    try:
        with neo4j_session() as session:
            session.run("RETURN 1").consume()
        return True
    except Exception:
        return False


def shutdown():
    """Закрыть driver при остановке приложения."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None