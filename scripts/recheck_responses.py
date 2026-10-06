"""
Пересчитывает поле correct у всех существующих ответов
по актуальной логике сравнения.
Использование:
    python scripts/recheck_responses.py
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from ingest.normalize import answers_equal

load_dotenv()

DB_URL = os.getenv("HYPERUM_DB_URL")
TENANT = os.getenv("HYPERUM_TENANT_DEFAULT", "school_lyceum")
engine = create_engine(DB_URL)

SELECT = text("""
    SELECT r.id, r.answer, t.answer AS expected, t.type
    FROM responses r
    JOIN tasks t ON t.id = r.task_id
    WHERE r.tenant_id = :t
""")

UPDATE = text("UPDATE responses SET correct = :c WHERE id = :id")

with engine.begin() as conn:
    rows = conn.execute(SELECT, {"t": TENANT}).fetchall()
    changed = 0
    for resp_id, answer, expected, task_type in rows:
        new_correct = answers_equal(answer, expected, task_type or "text")
        conn.execute(UPDATE, {"c": new_correct, "id": resp_id})
        changed += 1
    print(f"Пересчитано ответов: {changed}")