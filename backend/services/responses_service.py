"""
Бизнес-логика ответов учеников.
Проверка через ingest.normalize, обновление mastery, sync в Neo4j.
"""
import math
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session

from ingest.normalize import answers_equal
from backend.db.neo4j import neo4j_session


# ─── Параметры обновления mastery ────────────────────────────

PRIOR = 0.5       # сглаживание к среднему при малом числе попыток
WEIGHT = 3.0      # «вес» prior'а (сколько виртуальных попыток)


def _mark_assignment_completed_if_done(
    session: Session,
    tenant_id: str,
    student_id: UUID | str,
    task_id: UUID | str,
) -> None:
    """
    Проверяет, все ли задания текущего assignment покрыты ответами,
    и если да — ставит status='completed'.
    """
    # Находим assignment по task_id и student_id
    row = session.execute(text("""
        SELECT at.assignment_id
        FROM assignment_tasks at
        WHERE at.task_id = :tid AND at.student_id = :sid
        LIMIT 1
    """), {"tid": str(task_id), "sid": str(student_id)}).fetchone()

    if not row:
        return

    assignment_id = row[0]

    # Сколько заданий всего и сколько покрыто
    stats = session.execute(text("""
        SELECT
            (SELECT COUNT(*) FROM assignment_tasks
             WHERE assignment_id = :aid AND student_id = :sid) AS total,
            (SELECT COUNT(DISTINCT r.task_id) FROM responses r
             JOIN assignment_tasks at
               ON at.task_id = r.task_id AND at.assignment_id = :aid
             WHERE at.student_id = :sid
               AND r.student_id = :sid
               AND (r.correct IS NOT NULL OR r.skipped = TRUE)
            ) AS done
    """), {"aid": str(assignment_id), "sid": str(student_id)}).fetchone()

    if stats and stats[0] > 0 and stats[0] == stats[1]:
        session.execute(text("""
            UPDATE assignment_students
            SET status = 'completed', completed_at = now()
            WHERE assignment_id = :aid
              AND student_id = :sid
              AND status != 'completed'
        """), {"aid": str(assignment_id), "sid": str(student_id)})

def _smoothed_mastery(correct: int, attempts: int) -> float:
    """
    Байесовское сглаживание mastery.
    При малом числе попыток тянем к 0.5, при большом — доверяем данным.
    """
    return (correct + PRIOR * WEIGHT) / (attempts + WEIGHT)


# ─── Проверка ответа ─────────────────────────────────────────

def check_answer(
    session: Session,
    task_id: UUID,
    student_answer: str,
) -> dict | None:
    """
    Проверить ответ.
    Возвращает {correct, expected, task_type} или None, если задание не найдено.
    """
    row = session.execute(text("""
        SELECT answer, type FROM tasks WHERE id = :tid
    """), {"tid": str(task_id)}).fetchone()

    if row is None:
        return None

    expected, task_type = row[0], row[1] or "text"
    correct = answers_equal(student_answer, expected, task_type)

    return {
        "correct": correct,
        "expected": expected,
        "task_type": task_type,
    }


# ─── Сохранение и обновление ─────────────────────────────────

def save_response(
    session: Session,
    tenant_id: str,
    student_id: UUID | str,
    task_id: UUID | str,
    answer: str,
    correct: bool,
    time_sec: int | None = None,
) -> str:
    """
    Записать ответ в БД. Возвращает UUID ответа.
    """
    response_id = session.execute(text("""
        INSERT INTO responses
            (tenant_id, student_id, task_id, answer, correct, time_sec)
        VALUES
            (:t, :s, :task, :a, :c, :time)
        RETURNING id
    """), {
        "t": tenant_id, "s": str(student_id),
        "task": str(task_id), "a": answer,
        "c": correct, "time": time_sec,
    }).scalar()
    return str(response_id)


def get_task_skills(session: Session, task_id: UUID | str) -> list[str]:
    """Навыки, которые проверяет задание (по разметке deepseek)."""
    rows = session.execute(text("""
        SELECT skill_id FROM task_labels
        WHERE task_id = :tid AND model = 'deepseek'
    """), {"tid": str(task_id)}).fetchall()
    return [r[0] for r in rows]


def update_mastery(
    session: Session,
    tenant_id: str,
    student_id: UUID | str,
    skill_id: str,
) -> float:
    """
    Пересчитать mastery по навыку на основе всех ответов ученика.
    Возвращает новое значение.
    """
    # Считаем агрегаты по всем ответам на этот навык
    row = session.execute(text("""
        SELECT
            COUNT(*) AS attempts,
            SUM(CASE WHEN r.correct THEN 1 ELSE 0 END) AS correct
        FROM responses r
        JOIN task_labels tl ON tl.task_id = r.task_id
        WHERE r.student_id = :sid
          AND tl.skill_id = :skill
          AND tl.model = 'deepseek'
          AND r.tenant_id = :t
    """), {
        "sid": str(student_id), "skill": skill_id, "t": tenant_id,
    }).fetchone()

    attempts = row[0] or 0
    correct = row[1] or 0
    mastery = _smoothed_mastery(correct, attempts)

    # Upsert в student_mastery
    session.execute(text("""
        INSERT INTO student_mastery
            (tenant_id, student_id, skill_id, mastery, attempts, correct, updated_at)
        VALUES
            (:t, :s, :skill, :m, :a, :c, now())
        ON CONFLICT (tenant_id, student_id, skill_id) DO UPDATE
          SET mastery = EXCLUDED.mastery,
              attempts = EXCLUDED.attempts,
              correct = EXCLUDED.correct,
              updated_at = now()
    """), {
        "t": tenant_id, "s": str(student_id), "skill": skill_id,
        "m": round(mastery, 4), "a": attempts, "c": correct,
    })

    return mastery


def sync_mastery_to_neo4j(
    student_id: UUID | str,
    skill_id: str,
    mastery: float,
    attempts: int,
    correct: int,
) -> None:
    """
    Обновить ребро MASTERY в Neo4j.
    Ошибки не критичны — не ломают ответ ученику.
    """
    try:
        with neo4j_session() as session:
            # Узел Student — создаём если нет
            session.run("""
                MERGE (st:Student {id: $sid})
                SET st.tenant_id = 'school_lyceum'
            """, sid=str(student_id))

            # Ребро MASTERY
            session.run("""
                MATCH (st:Student {id: $sid})
                MATCH (sk:Skill {id: $skill})
                MERGE (st)-[m:MASTERY]->(sk)
                SET m.value = $val,
                    m.attempts = $att,
                    m.correct = $cor,
                    m.updated_at = datetime()
            """, sid=str(student_id), skill=skill_id,
                 val=mastery, att=attempts, cor=correct)
    except Exception:
        # Neo4j недоступен — не критично
        pass


# ─── Полный цикл: приём ответа ───────────────────────────────

def submit_response(
    session: Session,
    tenant_id: str,
    student_id: UUID | str,
    task_id: UUID | str,
    answer: str,
    time_sec: int | None = None,
    skipped: bool = False,
) -> dict | None:
    # Проверка, что задание существует
    check = session.execute(text("""
        SELECT 1 FROM tasks WHERE id = :tid
    """), {"tid": str(task_id)}).fetchone()
    if not check:
        return None

    # Если это пропуск — не проверяем, не обновляем mastery
    if skipped:
        response_id = session.execute(text("""
            INSERT INTO responses
                (tenant_id, student_id, task_id, answer, correct, time_sec, skipped)
            VALUES
                (:t, :s, :task, '', NULL, :time, TRUE)
            RETURNING id
        """), {
            "t": tenant_id, "s": str(student_id),
            "task": str(task_id), "time": time_sec,
        }).scalar()

        return {
            "response_id": str(response_id),
            "correct": False,
            "expected": None,
            "new_mastery": None,
            "skipped": True,
        }

    # Обычная логика (проверка + сохранение + mastery)
    result = check_answer(session, task_id, answer)
    if result is None:
        return None

    response_id = save_response(
        session, tenant_id, student_id, task_id,
        answer, result["correct"], time_sec,
    )

    skill_ids = get_task_skills(session, task_id)
    new_mastery = None
    for skill_id in skill_ids:
        new_mastery = update_mastery(session, tenant_id, student_id, skill_id)
        stats = session.execute(text("""
            SELECT attempts, correct FROM student_mastery
            WHERE tenant_id = :t AND student_id = :s AND skill_id = :sk
        """), {"t": tenant_id, "s": str(student_id), "sk": skill_id}).fetchone()
        if stats:
            sync_mastery_to_neo4j(
                student_id, skill_id,
                new_mastery, stats[0], stats[1],
            )

    return {
        "response_id": response_id,
        "correct": result["correct"],
        "expected": result["expected"],
        "new_mastery": new_mastery,
        "skipped": False,
    }


# ─── История и статистика ────────────────────────────────────

def list_my_responses(
    session: Session,
    student_id: UUID | str,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    rows = session.execute(text("""
        SELECT r.id, r.task_id, t.code, t.text, t.answer,
               r.answer, r.correct, r.skipped, r.time_sec, r.created_at,
               a.title AS assignment_title,
               s.name AS skill_name
        FROM responses r
        JOIN tasks t ON t.id = r.task_id
        LEFT JOIN assignment_tasks at
          ON at.task_id = r.task_id AND at.student_id = r.student_id
        LEFT JOIN assignments a ON a.id = at.assignment_id
        LEFT JOIN task_labels tl
          ON tl.task_id = r.task_id AND tl.model = 'deepseek'
        LEFT JOIN skills s ON s.id = tl.skill_id
        WHERE r.student_id = :sid
        ORDER BY r.created_at DESC
        LIMIT :lim OFFSET :off
    """), {"sid": str(student_id), "lim": limit, "off": offset}).fetchall()

    return [
        {
            "id": r[0], "task_id": r[1], "code": r[2],
            "task_text": r[3], "expected": r[4],
            "answer": r[5], "correct": r[6], "skipped": r[7],
            "time_sec": r[8], "created_at": r[9],
            "assignment_title": r[10], "skill_name": r[11],
        }
        for r in rows
    ]


def task_stats(session: Session, task_id: UUID | str) -> dict | None:
    """Статистика по заданию."""
    row = session.execute(text("""
        SELECT t.id, t.code,
               COUNT(r.id) AS attempts,
               SUM(CASE WHEN r.correct THEN 1 ELSE 0 END) AS correct
        FROM tasks t
        LEFT JOIN responses r ON r.task_id = t.id
        WHERE t.id = :tid
        GROUP BY t.id, t.code
    """), {"tid": str(task_id)}).fetchone()

    if row is None:
        return None

    attempts = row[2] or 0
    correct = row[3] or 0
    success_rate = correct / attempts if attempts else 0.0

    skill_row = session.execute(text("""
        SELECT skill_id FROM task_labels
        WHERE task_id = :tid AND model = 'deepseek'
        LIMIT 1
    """), {"tid": str(task_id)}).fetchone()

    return {
        "task_id": str(row[0]),
        "code": row[1],
        "attempts": attempts,
        "correct": correct,
        "success_rate": round(success_rate, 3),
        "skill_id": skill_row[0] if skill_row else None,
    }


def assignment_progress(
    session: Session,
    assignment_id: UUID | str,
    teacher_id: UUID | str,
) -> dict | None:
    """
    Прогресс по назначению.
    Только для автора назначения.
    """
    # Проверка владельца
    row = session.execute(text("""
        SELECT created_by, title FROM assignments WHERE id = :aid
    """), {"aid": str(assignment_id)}).fetchone()

    if row is None:
        return None
    if str(row[0]) != str(teacher_id):
        return None

    # Агрегаты
    stats = session.execute(text("""
        SELECT
            (SELECT COUNT(*) FROM assignment_students
             WHERE assignment_id = :aid) AS total_students,
            (SELECT COUNT(*) FROM assignment_students
             WHERE assignment_id = :aid AND status = 'completed') AS completed,
            (SELECT COUNT(*) FROM responses r
             JOIN assignment_tasks at ON at.task_id = r.task_id
                AND at.assignment_id = :aid
             WHERE r.student_id = at.student_id) AS total_attempts,
            (SELECT COUNT(*) FROM responses r
             JOIN assignment_tasks at ON at.task_id = r.task_id
                AND at.assignment_id = :aid
             WHERE r.student_id = at.student_id AND r.correct) AS total_correct
    """), {"aid": str(assignment_id)}).fetchone()

    total_students = stats[0] or 0
    completed = stats[1] or 0
    total_attempts = stats[2] or 0
    total_correct = stats[3] or 0
    correct_rate = total_correct / total_attempts if total_attempts else 0.0

        # Проверяем: все ли задания в assignment покрыты — если да, помечаем completed
    _mark_assignment_completed_if_done(
        session, tenant_id, student_id, task_id
    )

    return {
        "assignment_id": str(assignment_id),
        "title": row[1],
        "total_students": total_students,
        "completed_students": completed,
        "total_attempts": total_attempts,
        "correct_rate": round(correct_rate, 3),
    }