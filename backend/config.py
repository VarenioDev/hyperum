"""
Конфигурация приложения. Читает переменные из .env.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env из корня проекта
ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")


class Settings:
    # PostgreSQL
    DB_URL: str = os.getenv("HYPERUM_DB_URL", "")

    # Neo4j
    NEO4J_URI: str = os.getenv("HYPERUM_NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("HYPERUM_NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("HYPERUM_NEO4J_PASSWORD", "")

    # JWT
    JWT_SECRET: str = os.getenv("HYPERUM_JWT_SECRET", "change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_MINUTES: int = 60          # access-токен живёт 1 час
    JWT_REFRESH_DAYS: int = 30            # refresh-токен живёт 30 дней

    # Приложение
    TENANT_DEFAULT: str = os.getenv("HYPERUM_TENANT_DEFAULT", "school_lyceum")
    APP_TITLE: str = "HyperUm API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("HYPERUM_DEBUG", "false").lower() == "true"


settings = Settings()