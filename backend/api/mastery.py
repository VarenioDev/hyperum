"""
Роутер /mastery — аналитика освоения.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.auth.dependencies import get_current_user, require_teacher
from backend.db.postgres import tenant_session
from backend.models.responses import (
    StudentMastery, ClassMastery, ClassMasteryItem, MasteryItem, MasterySummary,
)
from backend.models.users import UserResponse
from backend.services import mastery_service


router = APIRouter(prefix="/mastery", tags=["mastery"])


@router.get("/me", response_model=StudentMastery)
async def my_mastery(
    user: UserResponse = Depends(get_current_user),
):
    """
    Mastery текущего пользователя.
    Для ученика — его собственный профиль.
    Для учителя — 400: учитель не имеет mastery.
    """
    if user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mastery доступен только ученикам. "
                   "Для просмотра ученика используйте /mastery/student/{id}",
        )

    with tenant_session(user.tenant_id) as session:
        result = mastery_service.get_student_mastery(session, user.id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль mastery не найден",
        )

    return result

@router.get("/me/summary", response_model=MasterySummary)
async def my_mastery_summary(
    user: UserResponse = Depends(get_current_user),
):
    """
    Краткая сводка mastery текущего ученика.
    Используется для метрик на дашборде.
    """
    if user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Только для учеников",
        )

    with tenant_session(user.tenant_id) as session:
        result = mastery_service.get_student_summary(session, user.id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль mastery не найден",
        )

    return result

@router.get("/student/{student_id}", response_model=StudentMastery)
async def student_mastery(
    student_id: UUID,
    user: UserResponse = Depends(require_teacher),
):
    """
    Mastery конкретного ученика.
    Доступно только учителю / администратору.
    """
    with tenant_session(user.tenant_id) as session:
        result = mastery_service.get_student_mastery(session, student_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ученик {student_id} не найден",
        )

    return result


@router.get("/student/{student_id}/weak", response_model=list[MasteryItem])
async def student_weak_skills(
    student_id: UUID,
    threshold: float = Query(0.5, ge=0.0, le=1.0,
                             description="Порог: ниже — считается слабым"),
    user: UserResponse = Depends(require_teacher),
):
    """
    Слабые навыки ученика (mastery < threshold).
    """
    with tenant_session(user.tenant_id) as session:
        return mastery_service.get_weak_skills(
            session, student_id, threshold=threshold
        )


@router.get("/class/{group_id}", response_model=ClassMastery)
async def class_mastery(
    group_id: UUID,
    user: UserResponse = Depends(require_teacher),
):
    """
    Агрегат mastery по классу.
    """
    with tenant_session(user.tenant_id) as session:
        class_name, skills = mastery_service.get_class_mastery(
            session, group_id
        )

    if class_name is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Класс {group_id} не найден",
        )

    return ClassMastery(class_name=class_name, skills=skills)


@router.get("/skills", response_model=list[ClassMasteryItem])
async def skills_summary(
    user: UserResponse = Depends(require_teacher),
):
    """
    Сводка по всем навыкам: средний mastery по tenant'у.
    Отсортировано от слабых к сильным.
    """
    with tenant_session(user.tenant_id) as session:
        return mastery_service.get_skills_summary(session)

