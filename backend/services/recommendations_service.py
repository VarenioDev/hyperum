"""
Бизнес-логика рекомендаций.
Подбор «следующего шага» — одного задания в зоне ближайшего развития.

Алгоритм:
1. Слабейший навык ученика (mastery ASC, attempts > 0),
   с пропуском заблокированных prerequisite.
2. Кандидаты — задания с primary_skill = этот навык.
3. Скоринг через score_task, топ-10.
4. Детерминированный выбор по seed от (student_id, дата).
"""
import hashlib
from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.recommendations import NextTaskRecommendation, RecommendedTask
from backend.services.assignments_service import (
    get_candidate_tasks,
    get_weak_prerequisites,
    score_task,
)
from backend.services import tasks_service


def _daily_seed(student_id: str, day: date) -> int:
    """Детерминированный seed для пары (ученик, день)."""
    raw = f"{student_id}:{day.isoformat()}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:4], "big")


def _build_reason(skill_name: str, mastery: float) -> str:
    if mastery < 0.3:
        level = "очень слабо"
    elif mastery < 0.5:
        level = "слабо"
    else:
        level = "средне"
    return (
        f"Навык «{skill_name}» — {level} освоен "
        f"({int(mastery * 100)}%). Задание подобрано "
        f"в зоне ближайшего развития."
    )


def get_next_task(
    session: Session,
    student_id: UUID | str,
) -> NextTaskRecommendation | None:
    """
    Подобрать одно задание для «следующего шага».
    Возвращает None, если у ученика нет mastery или нет заданий.
    """
    # 1. Все навыки ученика с попытками — от слабого к сильному
    weak_rows = session.execute(text("""
        SELECT sm.skill_id, s.name, sm.mastery
        FROM student_mastery sm
        JOIN skills s ON s.id = sm.skill_id
        WHERE sm.student_id = :sid AND sm.attempts > 0
        ORDER BY sm.mastery ASC
    """), {"sid": str(student_id)}).fetchall()

    if not weak_rows:
        return None

    # 2. Проверяем prerequisite для всех сразу
    all_ids = [r[0] for r in weak_rows]
    blocked = get_weak_prerequisites(str(student_id), all_ids)

    # Первый не заблокированный
    skill_id = None
    skill_name = None
    skill_mastery = None
    for r in weak_rows:
        if r[0] not in blocked:
            skill_id, skill_name, skill_mastery = r
            break

    if skill_id is None:
        # Все навыки заблокированы — нечего показать
        return None

    # 3. Кандидаты по этому навыку
    candidates = get_candidate_tasks(session, [skill_id], model="deepseek")
    if not candidates:
        return None

    # 4. Скоринг и топ-10
    mastery_map = {r[0]: float(r[2]) for r in weak_rows}
    scored = []
    for c in candidates:
        primary_m = mastery_map.get(c["primary_skill"], 0.5)
        secondaries = [
            mastery_map.get(s, 0.5)
            for s in c.get("all_skills", []) if s != c["primary_skill"]
        ]
        effective = (
            0.7 * primary_m + 0.3 * (sum(secondaries) / len(secondaries))
            if secondaries else primary_m
        )
        score = score_task(effective, c["difficulty"], usage_count=0)
        scored.append({**c, "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:10]

    # 5. Детерминированный выбор на сегодня
    seed = _daily_seed(str(student_id), date.today())
    chosen = top[seed % len(top)]

    # 6. Полные данные задания (type, options)
    full_task = tasks_service.get_task(session, UUID(chosen["task_id"]))
    if full_task is None:
        return None

    return NextTaskRecommendation(
        skill_id=skill_id,
        skill_name=skill_name,
        skill_mastery=round(float(skill_mastery), 3),
        reason=_build_reason(skill_name, float(skill_mastery)),
        task=RecommendedTask(
            task_id=full_task.id,
            code=full_task.code,
            text=full_task.text,
            type=full_task.type or "text",
            options=full_task.options,
            difficulty=chosen["difficulty"],
        ),
    )