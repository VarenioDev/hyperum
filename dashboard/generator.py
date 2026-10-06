"""
Генератор персональных тестов.
Ядро системы гиперперсонализации.
"""
import math
import os
import uuid
from typing import Any
import pandas as pd
from sqlalchemy import text
from neo4j import GraphDatabase

from db import query, get_engine


# ─── Neo4j ───────────────────────────────────────────────────

NEO4J_URI = os.getenv("HYPERUM_NEO4J_URI")
NEO4J_USER = os.getenv("HYPERUM_NEO4J_USER")
NEO4J_PASS = os.getenv("HYPERUM_NEO4J_PASSWORD")


# ─── Загрузка данных ─────────────────────────────────────────

def get_topics() -> list[str]:
    df = query("""
        SELECT DISTINCT topic FROM skills
        WHERE topic IS NOT NULL
        ORDER BY topic
    """)
    return df["topic"].tolist()


def get_group_id(class_name: str, tenant_id: str) -> str | None:
    df = query("""
        SELECT id FROM groups
        WHERE name = :c AND tenant_id = :t
        LIMIT 1
    """, {"c": class_name, "t": tenant_id})
    return df["id"].iloc[0] if not df.empty else None


def get_class_students(class_name: str, tenant_id: str) -> pd.DataFrame:
    return query("""
        SELECT u.id AS student_id, u.full_name,
               s.id AS skill_id, s.name AS skill_name,
               s.topic, sm.mastery
        FROM users u
        JOIN memberships m ON m.user_id = u.id AND m.role = 'student'
        JOIN groups g ON g.id = m.group_id
        LEFT JOIN student_mastery sm ON sm.student_id = u.id
        LEFT JOIN skills s ON s.id = sm.skill_id
        WHERE g.name = :c AND u.tenant_id = :t
        ORDER BY u.full_name, s.name
    """, {"c": class_name, "t": tenant_id})


def get_topic_skills(topic: str) -> pd.DataFrame:
    return query("""
        SELECT id, name FROM skills
        WHERE topic = :t
        ORDER BY id
    """, {"t": topic})


def get_candidate_tasks(skill_ids: list[str], model: str = "deepseek") -> pd.DataFrame:
    """
    Все задания, которые проверяют указанные навыки.
    Использует разметку указанной модели (по умолчанию — deepseek).
    """
    if not skill_ids:
        return pd.DataFrame()
    return query("""
        SELECT t.id AS task_id, t.code, t.text, t.answer,
               tl.skill_id, tl.difficulty
        FROM tasks t
        JOIN task_labels tl ON tl.task_id = t.id
        WHERE tl.skill_id = ANY(:sids)
          AND tl.model = :model
        ORDER BY t.code
    """, {"sids": skill_ids, "model": model})


# ─── Проверка prerequisite ───────────────────────────────────

def get_weak_prerequisites(student_id: str, skill_ids: list[str]) -> set[str]:
    """
    Возвращает skill_id, у которых у ученика провален prerequisite.
    Такие задания лучше не давать.
    """
    if not skill_ids:
        return set()

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        with driver.session() as session:
            result = session.run("""
                MATCH (st:Student {id: $stid})-[m:MASTERY]->(pre:Skill)
                WHERE m.value < 0.5
                MATCH (pre)-[:PREREQUISITE]->(target:Skill)
                WHERE target.id IN $sids
                RETURN DISTINCT target.id AS blocked
            """, stid=str(student_id), sids=skill_ids)
            blocked = {r["blocked"] for r in result}
        driver.close()
        return blocked
    except Exception:
        # Если Neo4j недоступен — не блокируем
        return set()


# ─── Логика подбора (IRT) ────────────────────────────────────

import random

def score_task(
    mastery: float,
    difficulty: float,
    usage_count: int = 0,
    diversity_weight: float = 0.5,
) -> float:
    """
    IRT-подобная оценка полезности задания с учётом diversity.

    - Оптимум P(правильно) ≈ 0.7 — зона ближайшего развития.
    - Бонус за слабые навыки (mastery < 0.5).
    - Штраф за частое использование у других учеников.
    """
    delta = mastery - difficulty
    p_correct = 1 / (1 + math.exp(-4 * delta))

    # Гауссовский пик вокруг 0.7
    base = math.exp(-((p_correct - 0.7) ** 2) / 0.08)

    # Приоритет слабым навыкам
    if mastery < 0.5:
        base *= 1.4

    # Штраф за повторное использование
    diversity_penalty = 1.0 / (1 + diversity_weight * usage_count)

    return base * diversity_penalty


def difficulty_band(d: float) -> str:
    """Разбить сложность на полосы по 0.1."""
    return f"{int(d * 10) / 10:.1f}"


def select_tasks_for_student(
    student_mastery: dict[str, float],
    candidates: pd.DataFrame,
    n: int = 5,
    max_per_skill: int = 2,
    max_per_band: int = 2,          # ← новое
    already_solved: set[str] | None = None,
    usage_counter: dict[str, int] | None = None,
) -> list[dict]:
    already_solved = already_solved or set()
    usage_counter = usage_counter or {}

    shuffled = candidates.sample(frac=1).reset_index(drop=True)

    scored = []
    for _, row in shuffled.iterrows():
        if row["task_id"] in already_solved:
            continue

        mastery = student_mastery.get(row["skill_id"], 0.5)
        usage = usage_counter.get(row["task_id"], 0)
        score = score_task(mastery, row["difficulty"], usage_count=usage)

        scored.append({
            "task_id": row["task_id"],
            "code": row["code"],
            "text": row["text"],
            "skill_id": row["skill_id"],
            "difficulty": row["difficulty"],
            "mastery": mastery,
            "usage": usage,
            "score": score,
            "band": difficulty_band(row["difficulty"]),  # ← новое
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    selected: list[dict] = []
    skill_counts: dict[str, int] = {}
    band_counts: dict[str, int] = {}   # ← новое

    for task in scored:
        if skill_counts.get(task["skill_id"], 0) >= max_per_skill:
            continue
        if band_counts.get(task["band"], 0) >= max_per_band:
            continue

        selected.append(task)
        skill_counts[task["skill_id"]] = skill_counts.get(task["skill_id"], 0) + 1
        band_counts[task["band"]] = band_counts.get(task["band"], 0) + 1

        if len(selected) == n:
            break

    # Добор без ограничений по band, но с сохранением skill-limit
    if len(selected) < n:
        selected_ids = {t["task_id"] for t in selected}
        for task in scored:
            if task["task_id"] in selected_ids:
                continue
            if skill_counts.get(task["skill_id"], 0) >= max_per_skill:
                continue
            selected.append(task)
            skill_counts[task["skill_id"]] = skill_counts.get(task["skill_id"], 0) + 1
            if len(selected) == n:
                break

    # Финальный добор без ограничений
    if len(selected) < n:
        selected_ids = {t["task_id"] for t in selected}
        for task in scored:
            if task["task_id"] in selected_ids:
                continue
            selected.append(task)
            if len(selected) == n:
                break

    return selected[:n]


# ─── Главная функция ─────────────────────────────────────────

def generate_for_class(
    class_name: str,
    topic: str,
    n_tasks: int,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Сгенерировать персональные тесты для всего класса.
    Учитывает diversity — задания, уже выданные другим,
    получают пониженный приоритет.
    """
    student_data = get_class_students(class_name, tenant_id)
    if student_data.empty:
        return {"error": "В классе нет учеников"}

    topic_skills = get_topic_skills(topic)
    if topic_skills.empty:
        return {"error": f"По теме «{topic}» нет навыков"}
    skill_ids = topic_skills["id"].tolist()

    candidates = get_candidate_tasks(skill_ids)
    if candidates.empty:
        return {"error": f"По теме «{topic}» нет заданий"}

    # Счётчик использования заданий (общий для всей генерации)
    usage_counter: dict[str, int] = {}

    students_result = []

    # Сортируем учеников случайно — тогда «первый ученик» тоже
    # каждый раз разный, и diversity распределится честнее
    student_ids = list(student_data.groupby("student_id"))
    random.shuffle(student_ids)

    for student_id, group in student_ids:
        full_name = group["full_name"].iloc[0]
        mastery = dict(
            zip(
                group["skill_id"].dropna(),
                group["mastery"].fillna(0.5),
            )
        )

        # Проверка prerequisite через Neo4j
        blocked = get_weak_prerequisites(str(student_id), skill_ids)
        candidates_filtered = candidates[
            ~candidates["skill_id"].isin(blocked)
        ] if blocked else candidates

        if candidates_filtered.empty:
            candidates_filtered = candidates

        tasks = select_tasks_for_student(
            mastery,
            candidates_filtered,
            n=n_tasks,
            usage_counter=usage_counter,
        )

        # Обновляем счётчик
        for t in tasks:
            tid = t["task_id"]
            usage_counter[tid] = usage_counter.get(tid, 0) + 1

        students_result.append({
            "student_id": student_id,
            "full_name": full_name,
            "tasks": tasks,
            "blocked_skills": list(blocked),
        })

    # Возвращаем в исходном порядке (по классу/имени)
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
    result: dict,
    group_id: str,
    created_by: str,
    tenant_id: str,
    title: str,
) -> str:
    """Сохранить сгенерированный тест как черновик."""
    engine = get_engine()
    assignment_id = str(uuid.uuid4())

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO assignments
                (id, tenant_id, group_id, created_by, topic, title, tasks_per_student, status)
            VALUES
                (:id, :t, :g, :cb, :topic, :title, :n, 'draft')
        """), {
            "id": assignment_id, "t": tenant_id, "g": group_id,
            "cb": created_by, "topic": result["topic"],
            "title": title, "n": result["n_tasks"],
        })

        for student in result["students"]:
            if not student["tasks"]:
                continue

            conn.execute(text("""
                INSERT INTO assignment_students (assignment_id, student_id, status)
                VALUES (:aid, :sid, 'pending')
            """), {"aid": assignment_id, "sid": student["student_id"]})

            for pos, task in enumerate(student["tasks"], start=1):
                conn.execute(text("""
                    INSERT INTO assignment_tasks
                        (assignment_id, student_id, task_id, position)
                    VALUES (:aid, :sid, :tid, :pos)
                """), {
                    "aid": assignment_id,
                    "sid": student["student_id"],
                    "tid": task["task_id"],
                    "pos": pos,
                })

    return assignment_id