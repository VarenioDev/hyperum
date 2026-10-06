"""
Считает mastery ученика по навыкам на основе responses + task_labels.
mastery = correct / attempts.
Идемпотентно: перезаписывает student_mastery.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_URL = os.getenv("HYPERUM_DB_URL")
TENANT = os.getenv("HYPERUM_TENANT_DEFAULT", "school_lyceum")
engine = create_engine(DB_URL)

AGG_QUERY = text("""
    WITH raw AS (
        SELECT r.student_id,
               tl.skill_id,
               r.correct
        FROM responses r
        JOIN task_labels tl ON tl.task_id = r.task_id
        WHERE r.tenant_id = :tenant
    )
    SELECT student_id,
           skill_id,
           COUNT(*) AS attempts,
           SUM(CASE WHEN correct THEN 1 ELSE 0 END) AS correct
    FROM raw
    GROUP BY student_id, skill_id
""")

UPSERT = text("""
    INSERT INTO student_mastery
        (tenant_id, student_id, skill_id, mastery, attempts, correct, updated_at)
    VALUES
        (:tenant, :student, :skill, :mastery, :attempts, :correct, now())
    ON CONFLICT (tenant_id, student_id, skill_id) DO UPDATE
    SET mastery = EXCLUDED.mastery,
        attempts = EXCLUDED.attempts,
        correct = EXCLUDED.correct,
        updated_at = now()
""")

with engine.begin() as conn:
    # 1. Очистить предыдущие значения по этому tenant
    conn.execute(text("DELETE FROM student_mastery WHERE tenant_id = :t"),
                 {"t": TENANT})

    # 2. Пересчитать
    rows = conn.execute(AGG_QUERY, {"tenant": TENANT}).fetchall()
    for r in rows:
        student, skill, attempts, correct = r
        mastery = correct / attempts if attempts else 0.0
        conn.execute(UPSERT, {
            "tenant": TENANT, "student": student, "skill": skill,
            "mastery": round(mastery, 4),
            "attempts": attempts, "correct": correct
        })
        print(f"  {str(student)[:8]}... {skill}: {mastery:.2f} ({correct}/{attempts})")

print(f"Mastery обновлён для {len(rows)} пар (ученик, навык).")