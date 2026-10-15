"""
Бизнес-логика ответов учеников.
Проверка через ingest.normalize, обновление mastery, sync в Neo4j,
автозакрытие assignment.
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


class InvalidAssignmentResponse(ValueError):
    pass


def _smoothed_mastery(correct: float, attempts: float) -> float:
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
    assignment_id: UUID | str | None = None,
) -> str:
    """Записать ответ в БД. Возвращает UUID ответа."""
    response_id = session.execute(text("""
        INSERT INTO responses
            (tenant_id, student_id, task_id, answer, correct, time_sec, assignment_id, context, created_at)
        VALUES
            (:t, :s, :task, :a, :c, :time, :aid, :context, clock_timestamp())
        RETURNING id
    """), {
        "t": tenant_id, "s": str(student_id),
        "task": str(task_id), "a": answer,
        "c": correct, "time": time_sec,
        "aid": str(assignment_id) if assignment_id else None,
        "context": 'assignment' if assignment_id else 'practice',
    }).scalar()
    return str(response_id)


def get_task_skills(session: Session, task_id: UUID | str) -> list[str]:
    """
    Навыки, которые проверяет задание.
    Primary идёт первым, secondary — после.
    """
    rows = session.execute(text("""
        SELECT skill_id FROM task_labels
        WHERE task_id = :tid AND model = 'deepseek'
        ORDER BY is_primary DESC, skill_id
    """), {"tid": str(task_id)}).fetchall()
    return [r[0] for r in rows]


def update_mastery(
    session: Session,
    tenant_id: str,
    student_id: UUID | str,
    skill_id: str,
) -> float:
    """
    Пересчитать mastery по навыку с учётом multi-skill разметки.

    Веса:
      - primary-навык задания → вес 1.0
      - secondary-навык задания → вес 0.7

    Mastery считается по взвешенным attempts/correct.
    В student_mastery пишутся «сырые» attempts/correct — для отображения.
    """
    # Взвешенные значения для расчёта mastery
    weighted_row = session.execute(text("""
        SELECT
            SUM(CASE WHEN tl.is_primary THEN 1.0 ELSE 0.7 END) AS w_attempts,
            SUM(
                CASE WHEN r.correct
                     THEN (CASE WHEN tl.is_primary THEN 1.0 ELSE 0.7 END)
                     ELSE 0
                END
            ) AS w_correct
        FROM responses r
        JOIN task_labels tl ON tl.task_id = r.task_id
        WHERE r.student_id = :sid
          AND tl.skill_id = :skill
          AND tl.model = 'deepseek'
          AND r.tenant_id = :t
    """), {
        "sid": str(student_id), "skill": skill_id, "t": tenant_id,
    }).fetchone()

    weighted_attempts = float(weighted_row[0] or 0)
    weighted_correct = float(weighted_row[1] or 0)
    mastery = _smoothed_mastery(weighted_correct, weighted_attempts)

    # Сырые значения для отображения
    raw_row = session.execute(text("""
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

    raw_attempts = int(raw_row[0] or 0)
    raw_correct = int(raw_row[1] or 0)

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
        "m": round(mastery, 4),
        "a": raw_attempts, "c": raw_correct,
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
            session.run("""
                MERGE (st:Student {id: $sid})
                SET st.tenant_id = 'school_lyceum'
            """, sid=str(student_id))

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


# ─── Автозакрытие assignment ─────────────────────────────────

def _mark_assignment_completed_if_done(
    session: Session,
    tenant_id: str,
    student_id: UUID | str,
    assignment_id: UUID | str,
) -> None:
    """
    Проверяет, все ли задания assignment покрыты ответами
    (с момента отправки теста), и если да — ставит completed.
    """
    stats = session.execute(text("""
        SELECT
            (SELECT COUNT(*) FROM assignment_tasks
             WHERE assignment_id = :aid AND student_id = :sid) AS total,
            (SELECT COUNT(DISTINCT r.task_id) FROM responses r
             JOIN assignment_tasks at
               ON at.task_id = r.task_id AND at.assignment_id = :aid
             WHERE at.student_id = :sid
               AND r.student_id = :sid
               AND r.assignment_id = :aid
               AND (r.correct IS NOT NULL OR r.skipped = TRUE)
            ) AS done
    """), {"aid": str(assignment_id), "sid": str(student_id)}).fetchone()

    if stats and stats[0] > 0:
        session.execute(text("""
            UPDATE assignment_students
            SET status = CASE WHEN :done = :total THEN 'completed' ELSE 'in_progress' END,
                completed_at = CASE WHEN :done = :total THEN COALESCE(completed_at, now()) ELSE NULL END
            WHERE assignment_id = :aid
              AND student_id = :sid
        """), {"aid": str(assignment_id), "sid": str(student_id), 'done': stats[1], 'total': stats[0]})


# ─── Полный цикл: приём ответа ───────────────────────────────

def submit_response(
    session: Session,
    tenant_id: str,
    student_id: UUID | str,
    task_id: UUID | str,
    answer: str,
    assignment_id: UUID | str | None = None,
    time_sec: int | None = None,
    skipped: bool = False,
    surrendered: bool = False,
) -> dict | None:
    """
    Полный цикл: проверка + сохранение + обновление mastery + автозакрытие.
    Возвращает словарь с результатом или None, если задание не найдено.
    """
    # Assignment context is explicit and checked before any answer is revealed or saved.
    if surrendered:
        skipped = True
    if assignment_id:
        allowed = session.execute(text("""
            SELECT 1 FROM assignment_tasks at
            JOIN assignments a ON a.id=at.assignment_id
            JOIN assignment_students ast ON ast.assignment_id=at.assignment_id AND ast.student_id=at.student_id
            JOIN memberships m ON m.group_id=a.group_id AND m.user_id=at.student_id
            WHERE at.assignment_id=:aid AND at.student_id=:sid AND at.task_id=:tid
              AND a.tenant_id=:tenant AND a.status IN ('sent','completed')
              AND m.role='student' AND m.status='active'
            FOR UPDATE OF ast
        """), {'aid': str(assignment_id), 'sid': str(student_id), 'tid': str(task_id), 'tenant': tenant_id}).fetchone()
        if not allowed:
            raise InvalidAssignmentResponse('Это задание недоступно в выбранном тесте')
    # Проверка, что задание существует
    check = session.execute(text("""
        SELECT 1 FROM tasks WHERE id = :tid
    """), {"tid": str(task_id)}).fetchone()
    if not check:
        return None

    # ─── Пропуск / сдача ─────────────────────────────────
    if skipped:
        response_id = session.execute(text("""
            INSERT INTO responses
                (tenant_id, student_id, task_id, answer, correct, time_sec,
                 skipped, surrendered, assignment_id, context, created_at)
            VALUES
                (:t, :s, :task, '', NULL, :time, TRUE, :surr, :aid, :context, clock_timestamp())
            RETURNING id
        """), {
            "t": tenant_id, "s": str(student_id),
            "task": str(task_id), "time": time_sec,
            "surr": surrendered,
            "aid": str(assignment_id) if assignment_id else None,
            "context": 'assignment' if assignment_id else 'practice',
        }).scalar()

        if assignment_id:
            _mark_assignment_completed_if_done(
                session, tenant_id, student_id, assignment_id
            )

        return {
            "response_id": str(response_id),
            "correct": False,
            "expected": None,
            "new_mastery": None,
            "skipped": True,
        }

    # ─── Обычный ответ ───────────────────────────────────
    result = check_answer(session, task_id, answer)
    if result is None:
        return None

    response_id = save_response(
        session, tenant_id, student_id, task_id,
        answer, result["correct"], time_sec, assignment_id,
    )

    skill_ids = get_task_skills(session, task_id)
    new_mastery = None
    for skill_id in skill_ids:
        m = update_mastery(session, tenant_id, student_id, skill_id)
        if new_mastery is None:
            new_mastery = m  # первый = primary
        stats = session.execute(text("""
            SELECT attempts, correct FROM student_mastery
            WHERE tenant_id = :t AND student_id = :s AND skill_id = :sk
        """), {"t": tenant_id, "s": str(student_id), "sk": skill_id}).fetchone()
        if stats:
            sync_mastery_to_neo4j(
                student_id, skill_id, m, stats[0], stats[1]
            )

    # Автозакрытие
    if assignment_id:
        _mark_assignment_completed_if_done(
            session, tenant_id, student_id, assignment_id
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
    """
    История ответов ученика.
    Один ответ — одна строка (берём primary-навык, чтобы не было дублей).
    """
    rows = session.execute(text("""
        SELECT
               r.id, r.task_id, t.code, t.text, t.answer,
               r.answer, r.correct, r.skipped, r.time_sec, r.created_at,
               a.title AS assignment_title,
               skill.name AS skill_name, r.context, r.surrendered
        FROM responses r
        JOIN tasks t ON t.id = r.task_id
        LEFT JOIN assignments a ON a.id = r.assignment_id
        LEFT JOIN LATERAL (
            SELECT s.name FROM task_labels tl JOIN skills s ON s.id=tl.skill_id
            WHERE tl.task_id=r.task_id AND tl.model='deepseek' AND tl.is_primary=TRUE
            ORDER BY tl.skill_id LIMIT 1
        ) skill ON TRUE
        WHERE r.student_id = :sid
        ORDER BY r.created_at DESC, r.id DESC
        LIMIT :lim OFFSET :off
    """), {"sid": str(student_id), "lim": limit, "off": offset}).fetchall()

    result = [
        {
            "id": r[0], "task_id": r[1], "code": r[2],
            "task_text": r[3], "expected": r[4],
            "answer": r[5], "correct": r[6], "skipped": r[7],
            "time_sec": r[8], "created_at": r[9],
            "assignment_title": r[10], "skill_name": r[11],
            "context": r[12], "surrendered": r[13],
        }
        for r in rows
    ]
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return result


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
        ORDER BY is_primary DESC
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
    """Прогресс по назначению. Только для автора."""
    from backend.services.teacher_reporting import assignment_matrix
    from backend.services.reporting_access import ReportNotFound
    try:
        report = assignment_matrix(session, assignment_id, teacher_id)
    except ReportNotFound:
        return None
    summary = report['summary']
    attempts = session.execute(text("SELECT COUNT(*) FROM responses WHERE assignment_id=:aid"),
                               {'aid': str(assignment_id)}).scalar() or 0
    return dict(assignment_id=str(assignment_id), title=report['assignment']['title'],
                total_students=summary['students_count'], completed_students=summary['completed_count'],
                total_attempts=attempts,
                correct_rate=round(summary['correct_count']/summary['answered_count'], 3) if summary['answered_count'] else 0.0)
