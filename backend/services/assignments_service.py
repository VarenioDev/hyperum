"""
Бизнес-логика назначений (сгенерированных тестов).
Портирует логику из dashboard/generator.py в API.
"""
import math
import random
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db.neo4j import neo4j_session


# ─── Загрузка данных ─────────────────────────────────────────

def get_group_id(session: Session, class_name: str) -> str | None:
    row = session.execute(text("""
        SELECT id FROM groups
        WHERE name = :c AND kind = 'class'
        LIMIT 1
    """), {"c": class_name}).fetchone()
    return str(row[0]) if row else None


def get_group_students(session: Session, group_id: str) -> list[dict]:
    rows = session.execute(text("""
        SELECT DISTINCT u.id, u.full_name
        FROM users u
        JOIN memberships m ON m.user_id = u.id AND m.role = 'student'
        WHERE m.group_id = :gid AND m.status = 'active'
        ORDER BY u.full_name
    """), {"gid": group_id}).fetchall()
    return [{"id": str(r[0]), "full_name": r[1]} for r in rows]


def get_student_mastery(session: Session, student_id: str) -> dict[str, float]:
    rows = session.execute(text("""
        SELECT skill_id, mastery
        FROM student_mastery
        WHERE student_id = :sid
    """), {"sid": student_id}).fetchall()
    return {r[0]: float(r[1]) for r in rows}


def get_topic_skills(session: Session, topic: str) -> list[str]:
    rows = session.execute(text("""
        SELECT id FROM skills WHERE topic = :t ORDER BY id
    """), {"t": topic}).fetchall()
    return [r[0] for r in rows]


def get_candidate_tasks(
    session: Session, skill_ids: list[str], model: str = "deepseek"
) -> list[dict]:
    """
    Задания, связанные с любым из указанных навыков.
    Одно задание — одна строка (даже если связано с несколькими навыками).
    """
    if not skill_ids:
        return []

    rows = session.execute(text("""
        SELECT
            t.id AS task_id,
            t.code,
            t.text,
            MAX(CASE WHEN tl.is_primary THEN tl.skill_id END) AS primary_skill,
            array_agg(DISTINCT tl.skill_id) AS all_skills,
            AVG(tl.difficulty) AS difficulty
        FROM tasks t
        JOIN task_labels tl ON tl.task_id = t.id
        WHERE tl.skill_id = ANY(:sids)
          AND tl.model = :model
        GROUP BY t.id, t.code, t.text
        HAVING MAX(CASE WHEN tl.is_primary THEN tl.skill_id END) IS NOT NULL
        ORDER BY t.code
    """), {"sids": skill_ids, "model": model}).fetchall()

    return [
        {
            "task_id": str(r[0]),
            "code": r[1],
            "text": r[2],
            "primary_skill": r[3],
            "all_skills": list(r[4]) if r[4] else [],
            "difficulty": float(r[5]),
        }
        for r in rows
    ]


def get_topics(session: Session) -> list[str]:
    rows = session.execute(text("""
        SELECT DISTINCT topic FROM skills
        WHERE topic IS NOT NULL
        ORDER BY topic
    """)).fetchall()
    return [r[0] for r in rows]


# ─── Neo4j: prerequisite ─────────────────────────────────────

def get_weak_prerequisites(student_id: str, skill_ids: list[str]) -> set[str]:
    """
    Навыки, у которых у ученика провален prerequisite.
    Если в Neo4j нет узлов Student — вернёт пустое множество.
    """
    if not skill_ids:
        return set()
    try:
        with neo4j_session() as session:
            result = session.run("""
                MATCH (st:Student {id: $stid})-[m:MASTERY]->(pre:Skill)
                WHERE m.value < 0.5
                MATCH (pre)-[:PREREQUISITE]->(target:Skill)
                WHERE target.id IN $sids
                RETURN DISTINCT target.id AS blocked
            """, stid=student_id, sids=skill_ids)
            return {r["blocked"] for r in result}
    except Exception:
        return set()


# ─── Scoring (IRT + diversity) ───────────────────────────────

def score_task(mastery: float, difficulty: float, usage_count: int = 0) -> float:
    """
    IRT-подобная оценка полезности с учётом diversity.
    """
    delta = mastery - difficulty
    p_correct = 1 / (1 + math.exp(-4 * delta))
    base = math.exp(-((p_correct - 0.7) ** 2) / 0.08)
    if mastery < 0.5:
        base *= 1.4
    diversity_penalty = 1.0 / (1 + 0.5 * usage_count)
    return base * diversity_penalty


def _difficulty_band(d: float) -> str:
    return f"{int(d * 10) / 10:.1f}"


def select_tasks_for_student(
    mastery: dict[str, float],
    candidates: list[dict],
    n: int = 5,
    max_per_skill: int = 2,
    max_per_band: int = 2,
    usage_counter: dict[str, int] | None = None,
) -> list[dict]:
    """
    Выбор n заданий для ученика с учётом multi-skill.

    mastery для scoring — взвешенная: 0.7 × primary + 0.3 × avg(secondary).
    Diversity — по primary-навыку.
    """
    usage_counter = usage_counter or {}

    shuffled = list(candidates)
    random.shuffle(shuffled)

    scored = []
    for c in shuffled:
        primary = c["primary_skill"]
        all_skills = c.get("all_skills", [primary])

        # Взвешенная mastery
        primary_m = mastery.get(primary, 0.5)
        secondaries = [mastery.get(s, 0.5) for s in all_skills if s != primary]
        if secondaries:
            secondary_m = sum(secondaries) / len(secondaries)
            effective_mastery = 0.7 * primary_m + 0.3 * secondary_m
        else:
            effective_mastery = primary_m

        usage = usage_counter.get(c["task_id"], 0)
        s = score_task(effective_mastery, c["difficulty"], usage)

        scored.append({
            **c,
            "mastery": effective_mastery,
            "primary_mastery": primary_m,
            "usage": usage,
            "score": s,
            "band": _difficulty_band(c["difficulty"]),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    selected: list[dict] = []
    skill_counts: dict[str, int] = {}
    band_counts: dict[str, int] = {}

    for task in scored:
        primary = task["primary_skill"]
        if skill_counts.get(primary, 0) >= max_per_skill:
            continue
        if band_counts.get(task["band"], 0) >= max_per_band:
            continue
        selected.append(task)
        skill_counts[primary] = skill_counts.get(primary, 0) + 1
        band_counts[task["band"]] = band_counts.get(task["band"], 0) + 1
        if len(selected) == n:
            break

    # Добор без band-ограничения
    if len(selected) < n:
        ids = {t["task_id"] for t in selected}
        for task in scored:
            if task["task_id"] in ids:
                continue
            primary = task["primary_skill"]
            if skill_counts.get(primary, 0) >= max_per_skill:
                continue
            selected.append(task)
            skill_counts[primary] = skill_counts.get(primary, 0) + 1
            if len(selected) == n:
                break

    # Финальный добор
    if len(selected) < n:
        ids = {t["task_id"] for t in selected}
        for task in scored:
            if task["task_id"] in ids:
                continue
            selected.append(task)
            if len(selected) == n:
                break

    return selected[:n]


# ─── Генерация для класса ────────────────────────────────────

def generate_for_group(
    session: Session,
    group_id: str,
    topic: str,
    n_tasks: int,
    model: str = "deepseek",
) -> dict[str, Any]:
    # Получаем информацию о группе
    group_row = session.execute(text("""
        SELECT name FROM groups WHERE id = :gid
    """), {"gid": group_id}).fetchone()
    if not group_row:
        return {"error": "Класс не найден"}
    class_name = group_row[0]

    students = get_group_students(session, group_id)
    if not students:
        return {"error": f"В классе {class_name} нет активных учеников"}

    skill_ids = get_topic_skills(session, topic)
    if not skill_ids:
        return {"error": f"По теме «{topic}» нет навыков"}

    candidates = get_candidate_tasks(session, skill_ids, model=model)
    if not candidates:
        return {"error": f"По теме «{topic}» нет размеченных заданий"}

    usage_counter: dict[str, int] = {}
    students_result = []

    shuffled = list(students)
    random.shuffle(shuffled)

    for student in shuffled:
        mastery = get_student_mastery(session, student["id"])
        blocked = get_weak_prerequisites(student["id"], skill_ids)

# Убираем задания, у которых primary-навык заблокирован
        filtered = [c for c in candidates if c["primary_skill"] not in blocked] \
            if blocked else candidates
        if not filtered:
            filtered = candidates

        tasks = select_tasks_for_student(
            mastery, filtered, n=n_tasks, usage_counter=usage_counter
        )

        for t in tasks:
            usage_counter[t["task_id"]] = usage_counter.get(t["task_id"], 0) + 1

        students_result.append({
            "student_id": student["id"],
            "full_name": student["full_name"],
            "tasks": tasks,
            "blocked_skills": list(blocked),
        })

    students_result.sort(key=lambda x: x["full_name"])

    return {
        "class_name": class_name,
        "topic": topic,
        "n_tasks": n_tasks,
        "students": students_result,
        "usage_stats": {
            "total_tasks_used": sum(usage_counter.values()),
            "unique_tasks_used": len(usage_counter),
            "max_usage": max(usage_counter.values()) if usage_counter else 0,
        },
    }


# ─── Сохранение ──────────────────────────────────────────────

def save_assignment(
    session: Session,
    generated: dict,
    created_by: str,
    title: str,
    group_id: str,   # ← теперь обязательный параметр
) -> str:
    # Проверяем, что группа существует
    group_exists = session.execute(text("""
        SELECT 1 FROM groups WHERE id = :gid
    """), {"gid": group_id}).fetchone()
    if not group_exists:
        raise ValueError(f"Класс не найден")

    assignment_id = str(uuid.uuid4())

    session.execute(text("""
        INSERT INTO assignments
            (id, tenant_id, group_id, created_by, topic, title,
             tasks_per_student, status)
        VALUES
            (:id, :t, :g, :cb, :topic, :title, :n, 'draft')
    """), {
        "id": assignment_id, "t": "school_lyceum",
        "g": group_id, "cb": created_by,
        "topic": generated["topic"], "title": title,
        "n": generated["n_tasks"],
    })

    for student in generated["students"]:
        if not student["tasks"]:
            continue
        session.execute(text("""
            INSERT INTO assignment_students
                (assignment_id, student_id, status)
            VALUES (:aid, :sid, 'pending')
        """), {"aid": assignment_id, "sid": student["student_id"]})

        for pos, task in enumerate(student["tasks"], start=1):
            session.execute(text("""
                INSERT INTO assignment_tasks
                    (assignment_id, student_id, task_id, position)
                VALUES (:aid, :sid, :tid, :pos)
            """), {
                "aid": assignment_id, "sid": student["student_id"],
                "tid": task["task_id"], "pos": pos,
            })

    return assignment_id


# ─── Чтение ──────────────────────────────────────────────────

def list_assignments_for_teacher(
    session: Session, created_by: str
) -> list[dict]:
    rows = session.execute(text("""
        SELECT a.id, a.title, a.topic, a.status,
               g.name AS class_name,
               a.tasks_per_student,
               (SELECT COUNT(*) FROM assignment_students
                WHERE assignment_id = a.id) AS students_count,
               a.created_at
        FROM assignments a
        LEFT JOIN groups g ON g.id = a.group_id
        WHERE a.created_by = :cb
        ORDER BY a.created_at DESC
    """), {"cb": created_by}).fetchall()

    return [
        {
            "id": r[0], "title": r[1], "topic": r[2], "status": r[3],
            "class_name": r[4], "tasks_per_student": r[5],
            "students_count": r[6], "created_at": r[7],
        }
        for r in rows
    ]


def list_assignments_for_student(
    session: Session, student_id: str
) -> list[dict]:
    rows = session.execute(text("""
        SELECT a.id, a.title, a.topic, a.status, a.deadline, a.created_at,
               ast.status AS student_status,
               (SELECT COUNT(*) FROM assignment_tasks
                WHERE assignment_id = a.id AND student_id = :sid) AS task_count,
               (SELECT COUNT(DISTINCT r.task_id) FROM responses r
                JOIN assignment_tasks at
                  ON at.task_id = r.task_id AND at.assignment_id = a.id
                WHERE at.student_id = :sid
                  AND r.student_id = :sid
                  AND (r.correct IS NOT NULL OR r.skipped = TRUE)
               ) AS completed_count
        FROM assignments a
        JOIN assignment_students ast ON ast.assignment_id = a.id
        WHERE ast.student_id = :sid
          AND a.status IN ('sent', 'completed')
        ORDER BY a.created_at DESC
    """), {"sid": student_id}).fetchall()

    return [
        {
            "id": r[0], "title": r[1], "topic": r[2], "status": r[3],
            "deadline": r[4], "created_at": r[5],
            "student_status": r[6],
            "task_count": r[7], "completed_count": r[8],
        }
        for r in rows
    ]


def get_assignment_tasks(
    session: Session, assignment_id: str, student_id: str
) -> list[dict] | None:
    check = session.execute(text("""
        SELECT 1 FROM assignment_students
        WHERE assignment_id = :aid AND student_id = :sid
    """), {"aid": assignment_id, "sid": student_id}).fetchone()
    if not check:
        return None

    rows = session.execute(text("""
        SELECT at.position, t.id, t.code, t.text, t.type, t.options,
               t.answer AS expected,
               r.answer, r.correct, r.skipped, r.time_sec
        FROM assignment_tasks at
        JOIN tasks t ON t.id = at.task_id
        LEFT JOIN LATERAL (
            SELECT answer, correct, skipped, time_sec
            FROM responses
            WHERE task_id = at.task_id
              AND student_id = at.student_id
            ORDER BY created_at DESC
            LIMIT 1
        ) r ON TRUE
        WHERE at.assignment_id = :aid AND at.student_id = :sid
        ORDER BY at.position
    """), {"aid": assignment_id, "sid": student_id}).fetchall()

    result = []
    for r in rows:
        task_data = {
            "position": r[0], "task_id": str(r[1]), "code": r[2],
            "text": r[3], "type": r[4], "options": r[5],
            "previous_response": None,
        }

        # Есть ли предыдущий ответ (или пропуск)
        if r[7] is not None or r[9] is True:
            task_data["previous_response"] = {
                "answer": r[7] or "",
                "correct": r[8],
                "skipped": r[9] or False,
                "time_sec": r[10],
                "expected": r[6],
            }
        result.append(task_data)

    return result


def send_assignment(
    session: Session, assignment_id: str, teacher_id: str
) -> dict:
    """
    Отправить черновик ученикам (status: draft → sent).
    """
    # Проверяем, что это назначение учителя
    row = session.execute(text("""
        SELECT created_by, status FROM assignments WHERE id = :aid
    """), {"aid": assignment_id}).fetchone()

    if row is None:
        return {"error": "not_found"}
    if str(row[0]) != teacher_id:
        return {"error": "forbidden"}
    if row[1] != "draft":
        return {"error": f"already_{row[1]}"}

    session.execute(text("""
        UPDATE assignments
        SET status = 'sent', sent_at = now()
        WHERE id = :aid
    """), {"aid": assignment_id})

    count = session.execute(text("""
        SELECT COUNT(*) FROM assignment_students WHERE assignment_id = :aid
    """), {"aid": assignment_id}).scalar()

    return {"students_count": count}