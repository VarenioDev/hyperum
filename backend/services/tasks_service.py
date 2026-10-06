"""
Бизнес-логика для работы с заданиями.
"""
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.tasks import TaskResponse, TaskBrief, TaskLabel


def list_tasks(
    session: Session,
    tenant_id: str,
    skill_id: str | None = None,
    model: str | None = "deepseek",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[TaskBrief], int]:
    """
    Список заданий с фильтрами.
    Возвращает (список, общее_количество).
    """
    where = ["1=1"]
    params = {"limit": limit, "offset": offset, "tenant": tenant_id}

    if skill_id:
        where.append("tl.skill_id = :skill_id")
        params["skill_id"] = skill_id

    if model:
        where.append("tl.model = :model")
        params["model"] = model

    where_sql = " AND ".join(where)

    # Общее количество
    total = session.execute(text(f"""
        SELECT COUNT(DISTINCT t.id)
        FROM tasks t
        LEFT JOIN task_labels tl ON tl.task_id = t.id
        WHERE {where_sql}
    """), params).scalar() or 0

    # Список
    rows = session.execute(text(f"""
        SELECT DISTINCT t.id, t.code, t.text, tl.difficulty, tl.skill_id
        FROM tasks t
        LEFT JOIN task_labels tl ON tl.task_id = t.id
        WHERE {where_sql}
        ORDER BY t.code
        LIMIT :limit OFFSET :offset
    """), params).fetchall()

    tasks = [
        TaskBrief(
            id=r[0], code=r[1], text=r[2],
            difficulty=float(r[3]) if r[3] is not None else None,
            skill_id=r[4],
        )
        for r in rows
    ]
    return tasks, total


def get_task(session: Session, task_id: UUID) -> TaskResponse | None:
    """Одно задание со всеми разметками."""
    row = session.execute(text("""
        SELECT id, code, text, type, answer, options, visibility
        FROM tasks
        WHERE id = :tid
    """), {"tid": str(task_id)}).fetchone()

    if row is None:
        return None

    # Разметки
    labels_rows = session.execute(text("""
        SELECT skill_id, difficulty, confidence, model, reasoning
        FROM task_labels
        WHERE task_id = :tid
    """), {"tid": str(task_id)}).fetchall()

    labels = [
        TaskLabel(
            skill_id=r[0],
            difficulty=float(r[1]),
            confidence=float(r[2]) if r[2] is not None else None,
            model=r[3],
            reasoning=r[4],
        )
        for r in labels_rows
    ]

    return TaskResponse(
        id=row[0],
        code=row[1],
        text=row[2],
        type=row[3],
        answer=row[4],
        options=row[5],
        visibility=row[6],
        labels=labels,
    )


def get_task_labels(session: Session, task_id: UUID) -> list[TaskLabel]:
    """Только разметки задания."""
    rows = session.execute(text("""
        SELECT skill_id, difficulty, confidence, model, reasoning
        FROM task_labels
        WHERE task_id = :tid
        ORDER BY model, skill_id
    """), {"tid": str(task_id)}).fetchall()

    return [
        TaskLabel(
            skill_id=r[0],
            difficulty=float(r[1]),
            confidence=float(r[2]) if r[2] is not None else None,
            model=r[3],
            reasoning=r[4],
        )
        for r in rows
    ]