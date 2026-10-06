"""
HyperUm API — точка входа.

Запуск:
    uvicorn backend.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.models import TaskResponse

from backend.api import auth as auth_router
from backend.api import tasks as tasks_router
from backend.api import mastery as mastery_router
from backend.api import graph as graph_router
from backend.api import assignments as assignments_router
from backend.api import responses as responses_router 

from backend.config import settings
from backend.db import postgres, neo4j


# ─── Lifespan ────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения:
    - startup: проверяем соединения
    - shutdown: закрываем пулы
    """
    # Startup
    print(f"🚀 Starting {settings.APP_TITLE} v{settings.APP_VERSION}")

    if postgres.ping():
        print("✅ PostgreSQL: connected")
    else:
        print("❌ PostgreSQL: NOT available")

    if neo4j.ping():
        print("✅ Neo4j: connected")
    else:
        print("❌ Neo4j: NOT available")

    yield

    # Shutdown
    print("🛑 Shutting down...")
    postgres.shutdown()
    neo4j.shutdown()


# ─── Приложение ──────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="API системы гиперперсонализации HyperUm",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Роутеры ────────────────────────────────────────────────
app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(tasks_router.router, prefix="/api/v1")
app.include_router(mastery_router.router, prefix="/api/v1")
app.include_router(graph_router.router, prefix="/api/v1")
app.include_router(assignments_router.router, prefix="/api/v1")
app.include_router(responses_router.router, prefix="/api/v1")

@app.get("/debug/tenant-test", tags=["system"])
async def tenant_test():
    """Тестовый эндпоинт — проверка RLS."""
    from sqlalchemy import text
    from backend.db.postgres import tenant_session

    with tenant_session("school_lyceum") as session:
        count = session.execute(
            text("SELECT COUNT(*) FROM users")
        ).scalar()

    return {"tenant": "school_lyceum", "users_visible": count}


# ─── Системные эндпоинты ─────────────────────────────────────

@app.get("/health", tags=["system"])
async def health():
    """Общая проверка API."""
    return {
        "status": "ok",
        "service": settings.APP_TITLE,
        "version": settings.APP_VERSION,
    }


@app.get("/health/db", tags=["system"])
async def health_db():
    """Проверка подключений к БД."""
    return {
        "postgres": "ok" if postgres.ping() else "down",
        "neo4j": "ok" if neo4j.ping() else "down",
    }

@app.get("/debug/schema-demo", tags=["system"], response_model=TaskResponse)
async def schema_demo():
    """
    Демонстрация схемы. Используется для проверки,
    что Pydantic работает и схемы видны в /docs.
    """
    return {
        "id": "00000000-0000-0000-0000-000000000001",
        "code": "task_001",
        "text": "Сколько бит в 4 байтах?",
        "type": "text",
        "answer": "32",
        "difficulty": 0.2,
        "visibility": "shared",
        "labels": [],
    }

@app.get("/", tags=["system"])
async def root():
    """Корневой эндпоинт."""
    return {
        "message": "HyperUm API",
        "docs": "/docs",
        "health": "/health",
        "health_db": "/health/db",
    }