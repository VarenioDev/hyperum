"""
Создаёт 5 тестовых заданий с привязкой к навыкам.
Вручную, без LLM — для отладки пайплайна.
"""
import os
import uuid
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_URL = os.getenv("HYPERUM_DB_URL")
engine = create_engine(DB_URL)

TASKS = [
    {
        "code": "task_001",
        "text": "Сколько будет 1010₂ + 110₂? Ответ в десятичной.",
        "answer": "16",
        "type": "text",
        "skill": "s_base_to_dec",
        "difficulty": 0.4,
    },
    {
        "code": "task_002",
        "text": "Переведите число 255 из десятичной в шестнадцатеричную.",
        "answer": "FF",
        "type": "text",
        "skill": "s_dec_to_base",
        "difficulty": 0.5,
    },
    {
        "code": "task_003",
        "text": "Сколько будет 12₈ + 7₈? Ответ в восьмеричной.",
        "answer": "21",
        "type": "text",
        "skill": "s_arith_in_base",
        "difficulty": 0.65,
    },
    {
        "code": "task_004",
        "text": "Что выведет код: for i in range(3): print(i)",
        "answer": "0 1 2",
        "type": "text",
        "skill": "s_for",
        "difficulty": 0.3,
    },
    {
        "code": "task_005",
        "text": "Сколько раз выполнится тело цикла: for i in range(1, 10, 2)?",
        "answer": "5",
        "type": "text",
        "skill": "s_for",
        "difficulty": 0.45,
    },
]

with engine.begin() as conn:
    for t in TASKS:
        task_id = str(uuid.uuid4())
        # upsert по code
        existing = conn.execute(
            text("SELECT id FROM tasks WHERE code = :c"), {"c": t["code"]}
        ).fetchone()

        if existing:
            task_id = existing[0]
            conn.execute(text("""
                UPDATE tasks SET text=:text, answer=:answer, type=:type
                WHERE id=:id
            """), {"text": t["text"], "answer": t["answer"],
                   "type": t["type"], "id": task_id})
        else:
            conn.execute(text("""
                INSERT INTO tasks (id, code, text, answer, type, visibility)
                VALUES (:id, :code, :text, :answer, :type, 'shared')
            """), {"id": task_id, "code": t["code"], "text": t["text"],
                   "answer": t["answer"], "type": t["type"]})

        # привязка к навыку (ручная разметка)
        conn.execute(text("""
            INSERT INTO task_labels (task_id, skill_id, difficulty, confidence, model)
            VALUES (:tid, :sid, :d, 1.0, 'manual')
            ON CONFLICT (task_id, skill_id) DO UPDATE
              SET difficulty = EXCLUDED.difficulty, model = 'manual'
        """), {"tid": task_id, "sid": t["skill"], "d": t["difficulty"]})

        print(f"  {t['code']} -> {t['skill']}")

print("Done.")