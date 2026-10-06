"""
Бизнес-логика для аналитики mastery.
"""
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.responses import (
    MasteryItem, StudentMastery, ClassMasteryItem,
)


def get_student_mastery(
    session: Session,
    student_id: UUID | str,
) -> StudentMastery | None:
    """
    Полный профиль mastery одного ученика.
    Возвращает None, если ученик не найден.
    """
    # Сначала — ФИО
    user_row = session.execute(text("""
        SELECT id, full_name
        FROM users
        WHERE id = :sid AND role = 'student'
    """), {"sid": str(student_id)}).fetchone()

    if user_row is None:
        return None

    # Затем — mastery по каждому навыку
    rows = session.execute(text("""
        SELECT sm.skill_id, s.name,
               sm.mastery, sm.attempts, sm.correct, sm.updated_at
        FROM student_mastery sm
        JOIN skills s ON s.id = sm.skill_id
        WHERE sm.student_id = :sid
        ORDER BY s.module, s.topic, s.name
    """), {"sid": str(student_id)}).fetchall()

    skills = [
        MasteryItem(
            skill_id=r[0],
            skill_name=r[1],
            mastery=float(r[2]),
            attempts=r[3],
            correct=r[4],
            updated_at=r[5],
        )
        for r in rows
    ]

    return StudentMastery(
        student_id=user_row[0],
        full_name=user_row[1],
        skills=skills,
    )


def get_class_mastery(
    session: Session,
    group_id: UUID | str,
) -> tuple[str | None, list[ClassMasteryItem]]:
    """
    Агрегат mastery по классу.
    Возвращает (имя_класса, список_навыков).
    """
    # Имя класса
    group_row = session.execute(text("""
        SELECT name FROM groups WHERE id = :gid
    """), {"gid": str(group_id)}).fetchone()

    if group_row is None:
        return None, []

    class_name = group_row[0]

    # Агрегат по навыкам
    rows = session.execute(text("""
        SELECT s.id, s.name,
               ROUND(AVG(sm.mastery)::numeric, 3) AS avg_mastery,
               COUNT(DISTINCT sm.student_id) AS student_count
        FROM student_mastery sm
        JOIN users u ON u.id = sm.student_id
        JOIN memberships m ON m.user_id = u.id
        JOIN skills s ON s.id = sm.skill_id
        WHERE m.group_id = :gid
        GROUP BY s.id, s.name
        ORDER BY s.module, s.topic, s.name
    """), {"gid": str(group_id)}).fetchall()

    skills = [
        ClassMasteryItem(
            skill_id=r[0],
            skill_name=r[1],
            avg_mastery=float(r[2]),
            student_count=r[3],
        )
        for r in rows
    ]

    return class_name, skills


def get_skills_summary(
    session: Session,
) -> list[ClassMasteryItem]:
    """
    Сводка mastery по всем навыкам (по всему tenant'у).
    Используется для общей картины.
    """
    rows = session.execute(text("""
        SELECT s.id, s.name,
               ROUND(AVG(sm.mastery)::numeric, 3) AS avg_mastery,
               COUNT(DISTINCT sm.student_id) AS student_count
        FROM student_mastery sm
        JOIN skills s ON s.id = sm.skill_id
        GROUP BY s.id, s.name
        ORDER BY avg_mastery ASC
    """)).fetchall()

    return [
        ClassMasteryItem(
            skill_id=r[0],
            skill_name=r[1],
            avg_mastery=float(r[2]),
            student_count=r[3],
        )
        for r in rows
    ]


def get_weak_skills(
    session: Session,
    student_id: UUID | str,
    threshold: float = 0.5,
) -> list[MasteryItem]:
    """
    Навыки ученика ниже порога.
    Используется для рекомендаций и уведомлений.
    """
    rows = session.execute(text("""
        SELECT sm.skill_id, s.name,
               sm.mastery, sm.attempts, sm.correct, sm.updated_at
        FROM student_mastery sm
        JOIN skills s ON s.id = sm.skill_id
        WHERE sm.student_id = :sid AND sm.mastery < :thr
        ORDER BY sm.mastery ASC
    """), {"sid": str(student_id), "thr": threshold}).fetchall()

    return [
        MasteryItem(
            skill_id=r[0], skill_name=r[1],
            mastery=float(r[2]), attempts=r[3],
            correct=r[4], updated_at=r[5],
        )
        for r in rows
    ]