"""
Публичные эндпоинты демонстрационного режима.
Авторизация не требуется.
"""
from uuid import UUID
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import text

from backend.db.postgres import tenant_session
from backend.models.demo import (
    DemoStartRequest, DemoStartResponse, DemoTask,
    DemoResponseRequest, DemoResponseResult,
)
from backend.models.graph import StudentGraph, GraphNode, GraphEdge
from backend.services import demo_service as svc
from backend.services import responses_service


router = APIRouter(prefix="/demo", tags=["demo"])


def _client_ip(request: Request) -> str:
    """IP клиента с учётом X-Forwarded-For от Nginx."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/start", response_model=DemoStartResponse)
async def start(payload: DemoStartRequest, request: Request):
    """Создать демо-сессию по описанию."""
    ip = _client_ip(request)
    if not svc.check_rate_limit(ip, max_per_hour=5):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много демо-запусков. Попробуйте через час.",
        )

    try:
        with tenant_session(svc.DEMO_TENANT) as session:
            result = svc.start_demo(session, payload.description)
    except RuntimeError as e:
        raise HTTPException(400, detail=str(e))

    return DemoStartResponse(
        session_id=result["session_id"],
        topic=result["topic"],
        total_tasks=result["total_tasks"],
        reasoning=result["reasoning"],
        tasks=[DemoTask(**t) for t in result["tasks"]],
    )


@router.post("/response", response_model=DemoResponseResult)
async def response(payload: DemoResponseRequest):
    """Ответ ученика в демо."""
    with tenant_session(svc.DEMO_TENANT) as session:
        # Проверяем, что гость существует
        check = session.execute(text("""
            SELECT 1 FROM users
            WHERE id = :sid AND tenant_id = :t
        """), {"sid": str(payload.session_id), "t": svc.DEMO_TENANT}).fetchone()

        if not check:
            raise HTTPException(404, detail="Демо-сессия не найдена")

        result = responses_service.submit_response(
            session,
            tenant_id=svc.DEMO_TENANT,
            student_id=payload.session_id,
            task_id=payload.task_id,
            answer=payload.answer,
            time_sec=payload.time_sec,
        )

    if result is None:
        raise HTTPException(404, detail="Задание не найдено")

    return DemoResponseResult(
        correct=result["correct"],
        expected=result["expected"],
        new_mastery=result["new_mastery"],
    )


@router.get("/graph/{session_id}", response_model=StudentGraph)
async def graph(session_id: UUID):
    """Граф знаний гостя."""
    with tenant_session(svc.DEMO_TENANT) as session:
        # ФИО гостя
        user_row = session.execute(text("""
            SELECT id, full_name FROM users
            WHERE id = :sid AND tenant_id = :t
        """), {"sid": str(session_id), "t": svc.DEMO_TENANT}).fetchone()

        if not user_row:
            raise HTTPException(404, detail="Демо-сессия не найдена")

        # Mastery
        mastery_rows = session.execute(text("""
            SELECT skill_id, mastery FROM student_mastery
            WHERE student_id = :sid
        """), {"sid": str(session_id)}).fetchall()
        mastery = {r[0]: float(r[1]) for r in mastery_rows}

    # Из Neo4j — структура графа
    from backend.services.graph_service import _fetch_full_graph, _mastery_status
    nodes_raw, edges_raw = _fetch_full_graph()

    nodes = []
    for n in nodes_raw:
        m = mastery.get(n["id"])
        nodes.append(GraphNode(
            id=n["id"], name=n["name"],
            module=n.get("module"), topic=n.get("topic"),
            mastery=m,
            status=_mastery_status(m),
        ))
    edges = [GraphEdge(**e) for e in edges_raw]

    return StudentGraph(
        student_id=str(user_row[0]),
        student_name=user_row[1],
        nodes=nodes,
        edges=edges,
    )