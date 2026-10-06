"""
Парсит CSV из Яндекс.Форм и пишет ответы в PostgreSQL.
Использование:
    python ingest/parse_yandex_csv.py data/test_responses.csv
"""
import os
import re
import sys
import uuid
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine, text

from ingest.normalize import answers_equal

load_dotenv()

DB_URL = os.getenv("HYPERUM_DB_URL")
TENANT = os.getenv("HYPERUM_TENANT_DEFAULT", "school_lyceum")
engine = create_engine(DB_URL)

TASK_CODE_RE = re.compile(r"\[(task_\w+)\]")


def get_or_create_student(conn, full_name: str, class_name: str) -> str:
    row = conn.execute(
        text("SELECT id FROM users WHERE full_name = :n AND tenant_id = :t"),
        {"n": full_name, "t": TENANT}
    ).fetchone()
    if row:
        return row[0]

    student_id = str(uuid.uuid4())
    conn.execute(text("""
        INSERT INTO users (id, tenant_id, role, full_name)
        VALUES (:id, :t, 'student', :n)
    """), {"id": student_id, "t": TENANT, "n": full_name})

    group = conn.execute(
        text("SELECT id FROM groups WHERE name = :n AND tenant_id = :t"),
        {"n": class_name, "t": TENANT}
    ).fetchone()
    if group:
        group_id = group[0]
    else:
        group_id = str(uuid.uuid4())
        conn.execute(text("""
            INSERT INTO groups (id, tenant_id, name, kind)
            VALUES (:id, :t, :n, 'class')
        """), {"id": group_id, "t": TENANT, "n": class_name})

    conn.execute(text("""
        INSERT INTO memberships (group_id, user_id, role)
        VALUES (:g, :u, 'student')
        ON CONFLICT DO NOTHING
    """), {"g": group_id, "u": student_id})

    return student_id


def parse(path: str):
    # КЛЮЧЕВОЕ: всё читаем как строки, пустые ячейки — "".
    df = pd.read_csv(
        path,
        encoding="utf-8-sig",
        sep=None,
        engine="python",
        dtype=str,
        keep_default_na=False,
    )

    task_cols = {}
    for col in df.columns:
        m = TASK_CODE_RE.search(col)
        if m:
            task_cols[col] = m.group(1)

    if not task_cols:
        print("Не найдено ни одного [task_XXX] в заголовках.")
        return

    print(f"Найдено заданий: {len(task_cols)}")

    with engine.begin() as conn:
        tasks_meta = {}
        for code in task_cols.values():
            row = conn.execute(text(
                "SELECT id, answer, type FROM tasks WHERE code = :c"
            ), {"c": code}).fetchone()
            if row:
                tasks_meta[code] = {"id": row[0], "answer": row[1], "type": row[2]}
            else:
                print(f"  [WARN] Задание {code} не найдено, пропускаю.")

        total = 0
        for _, row in df.iterrows():
            full_name = str(row.get("ФИО", "")).strip()
            class_name = str(row.get("Класс", "")).strip()
            if not full_name:
                continue

            student_id = get_or_create_student(conn, full_name, class_name)

            for col, code in task_cols.items():
                if code not in tasks_meta:
                    continue

                answer = row[col]
                if not str(answer).strip():
                    continue

                meta = tasks_meta[code]
                correct = answers_equal(answer, meta["answer"], meta["type"])

                conn.execute(text("""
                    INSERT INTO responses (tenant_id, student_id, task_id, answer, correct)
                    VALUES (:t, :s, :task, :a, :c)
                """), {
                    "t": TENANT,
                    "s": student_id,
                    "task": meta["id"],
                    "a": str(answer).strip(),
                    "c": correct,
                })
                total += 1

        print(f"Записано ответов: {total}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python ingest/parse_yandex_csv.py <path.csv>")
        sys.exit(1)
    parse(sys.argv[1])