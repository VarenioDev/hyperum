"""
Логика демонстрационного режима.
Гость описывает свой уровень → LLM разбирает → генерируем тест.
"""
import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.services.assignments_service import (
    get_topic_skills,
    get_candidate_tasks,
    select_tasks_for_student,
    get_topics,
)


DEMO_TENANT = "demo"
DEMO_GROUP_ID = "dddddddd-dddd-dddd-dddd-dddddddddddd"
DEMO_TTL_HOURS = 24
DEMO_N_TASKS = 5

DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


# ─── Rate limiting (простой in-memory) ────────────────────

_rate_limit: dict[str, list[datetime]] = {}


def check_rate_limit(ip: str, max_per_hour: int = 5) -> bool:
    """True — можно, False — лимит исчерпан."""
    now = datetime.now(timezone.utc)
    hour_ago = now - timedelta(hours=1)
    times = [t for t in _rate_limit.get(ip, []) if t > hour_ago]
    if len(times) >= max_per_hour:
        return False
    times.append(now)
    _rate_limit[ip] = times
    return True


# ─── Cleanup старых гостей ────────────────────────────────

def cleanup_old_demos(session: Session) -> int:
    """Удаляет гостей старше DEMO_TTL_HOURS."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=DEMO_TTL_HOURS)

    rows = session.execute(text("""
        SELECT id FROM users
        WHERE tenant_id = :t
          AND role = 'student'
          AND created_at < :cutoff
    """), {"t": DEMO_TENANT, "cutoff": cutoff}).fetchall()

    if not rows:
        return 0

    ids = [str(r[0]) for r in rows]

    for table, col in [
        ("responses", "student_id"),
        ("student_mastery", "student_id"),
        ("assignment_tasks", "student_id"),
        ("assignment_students", "student_id"),
        ("memberships", "user_id"),
        ("users", "id"),
    ]:
        session.execute(
            text(f"DELETE FROM {table} WHERE {col} = ANY(:ids)"),
            {"ids": ids},
        )

    return len(ids)


# ─── Разбор описания через LLM ────────────────────────────

PARSE_PROMPT = """Ты — методист по информатике. Студент описал свой уровень так:

"{description}"

Доступные навыки (ID | название):
{taxonomy}

Определи:
1. ОДНУ тему (topic) из списка доступных тем — по которой стоит проверить студента.
2. 2-5 навыков (skill_id), которые студент, судя по описанию, ЗНАЕТ.
3. 3-7 навыков (skill_id), которые студент НЕ знает.

Верни JSON строго:
{{
  "topic": "Название темы (точно как в таксономии)",
  "skills_known": ["s_xxx"],
  "skills_unknown": ["s_yyy"],
  "reasoning": "Краткое пояснение"
}}"""


def _load_taxonomy_text(session: Session) -> tuple[str, list[str]]:
    """Возвращает (текст_таксономии, список_всех_топиков)."""
    rows = session.execute(text("""
        SELECT id, name, topic FROM skills
        WHERE topic IS NOT NULL
        ORDER BY topic, id
    """)).fetchall()

    lines = []
    topics_set = set()
    for r in rows:
        lines.append(f'{r[0]} | {r[1]} | тема: {r[2]}')
        topics_set.add(r[2])

    return "\n".join(lines), sorted(topics_set)


def parse_description_with_llm(
    session: Session,
    description: str,
) -> dict:
    """Отправляет описание в DeepSeek, получает topic + known/unknown."""
    if not DEEPSEEK_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY не задан")

    taxonomy_text, topics = _load_taxonomy_text(session)
    prompt = PARSE_PROMPT.format(
        description=description,
        taxonomy=taxonomy_text,
    )

    response = requests.post(
        DEEPSEEK_URL,
        headers={
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": DEEPSEEK_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
        },
        timeout=60,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    data = json.loads(content)

    # Валидация: если topic не из таксономии — берём случайную
    if data.get("topic") not in topics:
        data["topic"] = random.choice(topics)

    return {
        "topic": data["topic"],
        "skills_known": data.get("skills_known", []),
        "skills_unknown": data.get("skills_unknown", []),
        "reasoning": data.get("reasoning", ""),
    }


# ─── Создание гостя ───────────────────────────────────────

def create_guest(session: Session) -> str:
    """Создаёт гостевого ученика. Возвращает UUID."""
    student_id = str(uuid.uuid4())
    guest_name = f"Гость-{student_id[:6].upper()}"

    session.execute(text("""
        INSERT INTO users (id, tenant_id, role, full_name, status)
        VALUES (:id, :t, 'student', :name, 'active')
    """), {"id": student_id, "t": DEMO_TENANT, "name": guest_name})

    session.execute(text("""
        INSERT INTO memberships (group_id, user_id, role, status)
        VALUES (:gid, :uid, 'student', 'active')
    """), {"gid": DEMO_GROUP_ID, "uid": student_id})

    return student_id


# ─── Старт демо ───────────────────────────────────────────

def start_demo(
    session: Session,
    description: str,
) -> dict:
    """
    Полный цикл:
    1. Разбор описания через LLM.
    2. Создание гостя.
    3. Установка mastery по навыкам.
    4. Генерация теста.
    """
    # Cleanup старых гостей
    cleanup_old_demos(session)

    # Разбор описания
    profile = parse_description_with_llm(session, description)
    topic = profile["topic"]

    # Создание гостя
    student_id = create_guest(session)

    # Установка mastery
    for skill_id in profile["skills_known"]:
        session.execute(text("""
            INSERT INTO student_mastery
                (tenant_id, student_id, skill_id, mastery, attempts, correct)
            VALUES (:t, :s, :sk, 0.85, 3, 3)
            ON CONFLICT (tenant_id, student_id, skill_id) DO UPDATE
              SET mastery = 0.85, attempts = 3, correct = 3
        """), {"t": DEMO_TENANT, "s": student_id, "sk": skill_id})

    for skill_id in profile["skills_unknown"]:
        session.execute(text("""
            INSERT INTO student_mastery
                (tenant_id, student_id, skill_id, mastery, attempts, correct)
            VALUES (:t, :s, :sk, 0.15, 3, 0)
            ON CONFLICT (tenant_id, student_id, skill_id) DO UPDATE
              SET mastery = 0.15, attempts = 3, correct = 0
        """), {"t": DEMO_TENANT, "s": student_id, "sk": skill_id})

    # Генерация теста
    skill_ids = get_topic_skills(session, topic)
    if not skill_ids:
        raise RuntimeError(f"По теме «{topic}» нет навыков")

    candidates = get_candidate_tasks(session, skill_ids, model="deepseek")
    if not candidates:
        raise RuntimeError(f"По теме «{topic}» нет размеченных заданий")

    # Загружаем mastery гостя
    mastery_rows = session.execute(text("""
        SELECT skill_id, mastery FROM student_mastery
        WHERE student_id = :s
    """), {"s": student_id}).fetchall()
    mastery = {r[0]: float(r[1]) for r in mastery_rows}

    selected = select_tasks_for_student(
        mastery, candidates, n=DEMO_N_TASKS
    )

    if not selected:
        raise RuntimeError("Не удалось подобрать задания")

    # Создаём assignment
    assignment_id = str(uuid.uuid4())
    session.execute(text("""
        INSERT INTO assignments
            (id, tenant_id, group_id, created_by, topic, title,
             tasks_per_student, status, sent_at)
        VALUES
            (:id, :t, :g, NULL, :topic, :title, :n, 'sent', now())
    """), {
        "id": assignment_id, "t": DEMO_TENANT, "g": DEMO_GROUP_ID,
        "topic": topic, "title": f"Демо — {topic}",
        "n": DEMO_N_TASKS,
    })

    session.execute(text("""
        INSERT INTO assignment_students (assignment_id, student_id, status)
        VALUES (:aid, :sid, 'pending')
    """), {"aid": assignment_id, "sid": student_id})

    for pos, task in enumerate(selected, 1):
        session.execute(text("""
            INSERT INTO assignment_tasks
                (assignment_id, student_id, task_id, position)
            VALUES (:aid, :sid, :tid, :pos)
        """), {
            "aid": assignment_id, "sid": student_id,
            "tid": task["task_id"], "pos": pos,
        })

    tasks_out = [
        {
            "task_id": t["task_id"],
            "code": t["code"],
            "text": t["text"],
            "position": pos,
        }
        for pos, t in enumerate(selected, 1)
    ]

    return {
        "session_id": student_id,
        "topic": topic,
        "total_tasks": len(selected),
        "reasoning": profile["reasoning"],
        "tasks": tasks_out,
    }