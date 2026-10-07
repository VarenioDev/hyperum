"""
Роутер /responses — ответы учеников.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.auth.dependencies import get_current_user, require_teacher
from backend.db.postgres import tenant_session
from backend.models.responses import (
    ResponseCreate, ResponseResult, ResponseResponse,
    TaskStat, AssignmentProgress,
)
from backend.models.users import UserResponse
from backend.services import responses_service as svc


router = APIRouter(prefix="/responses", tags=["responses"])


# ─── Отправка ответа (ученик) ────────────────────────────────

@router.post("", response_model=ResponseResult)
async def submit_response(
    payload: ResponseCreate,
    user: UserResponse = Depends(get_current_user),
):
    """
    Отправить ответ на задание.
    Возвращает: правильно/неправильно + новый mastery.
    """
    if user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только ученики могут отправлять ответы",
        )

    with tenant_session(user.tenant_id) as session:
        result = svc.submit_response(
        session,
        tenant_id=user.tenant_id,
        student_id=user.id,
        task_id=payload.task_id,
        answer=payload.answer,
        time_sec=payload.time_sec,
        skipped=payload.skipped,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задание не найдено",
        )

    return ResponseResult(
        correct=result["correct"],
        expected=result["expected"],
        explanation=None,
        new_mastery=result["new_mastery"],
    )


# ─── История (ученик) ────────────────────────────────────────

@router.get("/my", response_model=list[ResponseResponse])
async def my_responses(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: UserResponse = Depends(get_current_user),
):
    """История ответов текущего ученика."""
    if user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Только для учеников",
        )

    with tenant_session(user.tenant_id) as session:
        rows = svc.list_my_responses(
            session, user.id, limit=limit, offset=offset
        )

    return [ResponseResponse(**r) for r in rows]


# ─── Статистика (учитель) ────────────────────────────────────

@router.get("/task/{task_id}", response_model=TaskStat)
async def task_stat(
    task_id: UUID,
    user: UserResponse = Depends(require_teacher),
):
    """Статистика по заданию: сколько раз решали, сколько правильно."""
    with tenant_session(user.tenant_id) as session:
        result = svc.task_stats(session, task_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Задание {task_id} не найдено",
        )

    return TaskStat(**result)


@router.get("/assignment/{assignment_id}", response_model=AssignmentProgress)
async def assignment_progress(
    assignment_id: UUID,
    user: UserResponse = Depends(require_teacher),
):
    """Прогресс по назначению."""
    with tenant_session(user.tenant_id) as session:
        result = svc.assignment_progress(
            session, assignment_id, user.id
        )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Назначение не найдено или не ваше",
        )

    return AssignmentProgress(**result)