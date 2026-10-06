"""
Роутер /groups — классы и регистрация учеников.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException

from backend.auth.dependencies import require_teacher
from backend.db.postgres import tenant_session
from backend.models.groups import (
    GroupCreate, GroupResponse, GroupDetail, GroupByCode,
    JoinRequest, JoinResponse, ApproveResponse,
)
from backend.models.users import UserResponse
from backend.services import groups_service as svc


router = APIRouter(prefix="/groups", tags=["groups"])


# ─── Публичные эндпоинты (без авторизации) ──────────────────

@router.get("/by-code/{code}", response_model=GroupByCode)
async def get_by_code(code: str):
    """Публичная информация о классе по инвайт-коду."""
    with tenant_session("school_lyceum") as session:
        result = svc.get_group_by_code(session, code)

    if result is None:
        raise HTTPException(404, detail="Код класса не найден")

    return GroupByCode(**result)


@router.post("/join", response_model=JoinResponse)
async def join(payload: JoinRequest):
    """Регистрация ученика по инвайт-коду."""
    with tenant_session("school_lyceum") as session:
        try:
            result = svc.join_by_code(
                session,
                code=payload.code,
                full_name=payload.full_name,
                email=payload.email,
                password=payload.password,
            )
        except ValueError as e:
            raise HTTPException(400, detail=str(e))

    return JoinResponse(
        status=result["status"],
        message="Заявка отправлена. Учитель подтвердит её в ближайшее время.",
        group_name=result["group_name"],
    )


# ─── Эндпоинты учителя ──────────────────────────────────────

@router.post("", response_model=dict, status_code=201)
async def create_group(
    payload: GroupCreate,
    user: UserResponse = Depends(require_teacher),
):
    """Создать новый класс."""
    with tenant_session(user.tenant_id) as session:
        result = svc.create_group(
            session,
            tenant_id=user.tenant_id,
            owner_id=str(user.id),
            name=payload.name,
            subject=payload.subject,
            kind=payload.kind,
        )

    return result


@router.get("", response_model=list[GroupResponse])
async def list_groups(
    user: UserResponse = Depends(require_teacher),
):
    """Список классов учителя."""
    with tenant_session(user.tenant_id) as session:
        rows = svc.list_teacher_groups(session, str(user.id))

    return [GroupResponse(**r) for r in rows]


@router.get("/{group_id}", response_model=GroupDetail)
async def group_detail(
    group_id: UUID,
    user: UserResponse = Depends(require_teacher),
):
    """Детали класса: ученики, mastery."""
    with tenant_session(user.tenant_id) as session:
        result = svc.get_group_detail(session, group_id, str(user.id))

    if result is None:
        raise HTTPException(404, detail="Класс не найден или не ваш")

    return GroupDetail(**result)


@router.post("/{group_id}/regenerate-code", response_model=dict)
async def regenerate_code(
    group_id: UUID,
    user: UserResponse = Depends(require_teacher),
):
    """Сгенерировать новый инвайт-код."""
    with tenant_session(user.tenant_id) as session:
        code = svc.regenerate_code(session, group_id, str(user.id))

    if code is None:
        raise HTTPException(404, detail="Класс не найден или не ваш")

    return {"invite_code": code}


@router.post("/{group_id}/approve/{student_id}", response_model=ApproveResponse)
async def approve(
    group_id: UUID,
    student_id: UUID,
    user: UserResponse = Depends(require_teacher),
):
    """Подтвердить ученика."""
    with tenant_session(user.tenant_id) as session:
        ok = svc.approve_student(session, group_id, student_id, str(user.id))

    if not ok:
        raise HTTPException(404, detail="Класс или ученик не найден")

    return ApproveResponse(
        student_id=student_id,
        status="active",
        message="Ученик подтверждён",
    )


@router.post("/{group_id}/reject/{student_id}", response_model=ApproveResponse)
async def reject(
    group_id: UUID,
    student_id: UUID,
    user: UserResponse = Depends(require_teacher),
):
    """Отклонить заявку ученика."""
    with tenant_session(user.tenant_id) as session:
        ok = svc.reject_student(session, group_id, student_id, str(user.id))

    if not ok:
        raise HTTPException(404, detail="Класс или ученик не найден")

    return ApproveResponse(
        student_id=student_id,
        status="rejected",
        message="Заявка отклонена",
    )