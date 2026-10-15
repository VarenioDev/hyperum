"""
Роутер /graph — граф знаний.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.auth.dependencies import get_current_user, require_teacher
from backend.db.postgres import tenant_session
from backend.models.graph import GraphNode, GraphEdge, StudentGraph, ClassGraph
from backend.models.users import UserResponse
from backend.services import graph_service
from backend.services.reporting_access import owned_student, owned_class, ReportNotFound


router = APIRouter(prefix="/graph", tags=["graph"])


class FullGraphResponse(dict):
    """Просто dict для ответа — не критично для типизации."""
    pass


@router.get("/full", response_model=dict)
async def full_graph(
    user: UserResponse = Depends(get_current_user),
):
    """
    Полный предметный граф без mastery.
    Возвращает nodes[] и edges[] для Cytoscape.js.
    """
    with tenant_session(user.tenant_id) as session:
        nodes, edges = graph_service.get_full_graph(session)

    return {
        "nodes": [n.model_dump() for n in nodes],
        "edges": [e.model_dump() for e in edges],
    }


@router.get("/student/{student_id}", response_model=StudentGraph)
async def student_graph(
    student_id: UUID,
    user: UserResponse = Depends(get_current_user),
):
    """
    Граф ученика с раскраской по mastery.

    Доступ:
    - учитель/админ — любого ученика своего tenant'а
    - ученик — только свой граф
    """
    # Проверка прав: ученик может смотреть только себя
    if user.role == "student" and str(student_id) != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ученик может просматривать только свой граф",
        )

    with tenant_session(user.tenant_id) as session:
        if user.role in ('owner', 'admin'):
            try:
                owned_student(session, student_id, user.id)
            except ReportNotFound as exc:
                raise HTTPException(404, detail=str(exc)) from exc
        result = graph_service.get_student_graph(session, student_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ученик {student_id} не найден",
        )

    return result


@router.get("/class/{group_id}", response_model=ClassGraph)
async def class_graph(
    group_id: UUID,
    user: UserResponse = Depends(require_teacher),
):
    """Агрегированный граф класса."""
    with tenant_session(user.tenant_id) as session:
        try:
            owned_class(session, group_id, user.id)
        except ReportNotFound as exc:
            raise HTTPException(404, detail=str(exc)) from exc
        result = graph_service.get_class_graph(session, group_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Класс {group_id} не найден",
        )

    return result


@router.get("/skill/{skill_id}")
async def skill_subgraph(
    skill_id: str,
    depth: int = Query(3, ge=1, le=10,
                       description="Глубина обхода prerequisite"),
    user: UserResponse = Depends(get_current_user),
):
    """
    Подграф вокруг навыка: prerequisite-цепочка до указанной глубины.
    """
    nodes, edges = graph_service.get_skill_subgraph(skill_id)

    return {
        "root": skill_id,
        "depth": depth,
        "nodes": [n.model_dump() for n in nodes],
        "edges": [e.model_dump() for e in edges],
    }
