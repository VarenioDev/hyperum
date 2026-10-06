"""
Роутер /tasks — справочник заданий.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.auth.dependencies import get_current_user, require_teacher
from backend.db.postgres import tenant_session
from backend.models.common import PaginatedResponse, Pagination
from backend.models.tasks import TaskBrief, TaskResponse, TaskLabel
from backend.models.users import UserResponse
from backend.services import tasks_service


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=PaginatedResponse[TaskBrief])
async def list_tasks(
    skill_id: str | None = Query(None, description="Фильтр по навыку"),
    model: str | None = Query("deepseek", description="Модель разметки"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: UserResponse = Depends(get_current_user),
):
    """
    Список заданий с фильтрами.

    Доступен всем авторизованным пользователям.
    """
    with tenant_session(user.tenant_id) as session:
        tasks, total = tasks_service.list_tasks(
            session, user.tenant_id,
            skill_id=skill_id, model=model,
            limit=limit, offset=offset,
        )

    return PaginatedResponse[TaskBrief](
        items=tasks,
        pagination=Pagination(total=total, limit=limit, offset=offset),
    )

@router.get("/topics", response_model=list[str])
async def list_topics(
    user: UserResponse = Depends(get_current_user),
):
    """Список доступных тем (для генератора тестов)."""
    from sqlalchemy import text
    with tenant_session(user.tenant_id) as session:
        rows = session.execute(text("""
            SELECT DISTINCT topic FROM skills
            WHERE topic IS NOT NULL
            ORDER BY topic
        """)).fetchall()

    return [r[0] for r in rows]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    user: UserResponse = Depends(get_current_user),
):
    """Полное задание со всеми разметками."""
    with tenant_session(user.tenant_id) as session:
        task = tasks_service.get_task(session, task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Задание {task_id} не найдено",
        )

    return task


@router.get("/{task_id}/labels", response_model=list[TaskLabel])
async def get_task_labels(
    task_id: UUID,
    user: UserResponse = Depends(require_teacher),
):
    """
    Все разметки задания (GigaChat, DeepSeek, manual).
    Только для учителя — ученик не должен видеть разметку.
    """
    with tenant_session(user.tenant_id) as session:
        labels = tasks_service.get_task_labels(session, task_id)

    return labels