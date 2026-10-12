"""
Роутер /recommendations — рекомендации ученику.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth.dependencies import get_current_user
from backend.db.postgres import tenant_session
from backend.models.recommendations import NextTaskRecommendation
from backend.models.users import UserResponse
from backend.services import recommendations_service as svc


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/next", response_model=NextTaskRecommendation | None)
async def next_task(
    user: UserResponse = Depends(get_current_user),
):
    """
    Рекомендация «следующий шаг» — одно задание в зоне ближайшего развития.
    Возвращает null, если у ученика нет данных о mastery.
    """
    if user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Только для учеников",
        )

    with tenant_session(user.tenant_id) as session:
        result = svc.get_next_task(session, user.id)

    # None — валидный ответ: нечего рекомендовать
    return result