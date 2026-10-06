"""
Импорт заданий из CSV в HyperUm + автоматическая разметка через GigaChat.

Использование:
    python -m scripts.import_tasks tasks/informatics_10.csv
    python -m scripts.import_tasks tasks/informatics_10.csv --import-only
    python -m scripts.import_tasks --relabel

Режимы:
    (по умолчанию)  — импорт + разметка неразмеченных через GigaChat
    --import-only   — только импорт, без разметки
    --relabel       — переразметить все существующие задания
"""
import argparse
import os
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine, text

load_dotenv()
DB_URL = os.getenv("HYPERUM_DB_URL")
engine = create_engine(DB_URL)


# ─── Импорт из CSV ───────────────────────────────────────────

def import_csv(csv_path: str) -> tuple[int, int]:
    """
    Импортирует задания из CSV. Идемпотентно по code.
    Возвращает (created, updated).
    """
    df = pd.read_csv(csv_path, encoding="utf-8-sig", dtype=str, keep_default_na=False)

    required = {"code", "text", "answer"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"В CSV не хватает колонок: {missing}")

    created, updated = 0, 0

    with engine.begin() as conn:
        for _, row in df.iterrows():
            code = str(row["code"]).strip()
            text_val = str(row["text"]).strip()
            answer = str(row["answer"]).strip()
            task_type = str(row.get("type", "text")).strip() or "text"

            if not code or not text_val:
                print(f"  [SKIP] пустой code или text")
                continue

            existing = conn.execute(
                text("SELECT id FROM tasks WHERE code = :c"), {"c": code}
            ).fetchone()

            if existing:
                task_id = existing[0]
                conn.execute(text("""
                    UPDATE tasks
                    SET text = :text, answer = :answer, type = :type
                    WHERE id = :id
                """), {
                    "text": text_val, "answer": answer,
                    "type": task_type, "id": task_id,
                })
                updated += 1
                print(f"  [upd] {code}")
            else:
                task_id = str(uuid.uuid4())
                conn.execute(text("""
                    INSERT INTO tasks (id, code, text, answer, type, visibility)
                    VALUES (:id, :code, :text, :answer, :type, 'shared')
                """), {
                    "id": task_id, "code": code, "text": text_val,
                    "answer": answer, "type": task_type,
                })
                created += 1
                print(f"  [new] {code}")

    return created, updated


# ─── Разметка через GigaChat ─────────────────────────────────

def label_unlabeled() -> int:
    """
    Находит задания без разметки и размечает через GigaChat.
    Возвращает количество размеченных заданий.
    """
    from ml.label_tasks_with_gigachat import label_task

    with engine.begin() as conn:
        tasks = conn.execute(text("""
            SELECT t.id, t.code, t.text
            FROM tasks t
            LEFT JOIN task_labels tl ON tl.task_id = t.id
            WHERE tl.task_id IS NULL
            ORDER BY t.code
        """)).fetchall()

        if not tasks:
            print("  Неразмеченных заданий нет.")
            return 0

        print(f"  Найдено {len(tasks)} заданий без разметки.")

        count = 0
        for task_id, code, task_text in tasks:
            print(f"  [label] {code}...")
            label = label_task(task_text)
            if not label:
                print(f"    → ошибка разметки")
                continue

            conn.execute(text("""
                INSERT INTO task_labels
                    (task_id, skill_id, difficulty, confidence, model, reasoning)
                VALUES (:tid, :sid, :diff, :conf, 'gigachat', :reason)
                ON CONFLICT (task_id, skill_id) DO UPDATE
                  SET difficulty = EXCLUDED.difficulty,
                      confidence = EXCLUDED.confidence,
                      model = EXCLUDED.model,
                      reasoning = EXCLUDED.reasoning
            """), {
                "tid": task_id, "sid": label.skill_id,
                "diff": label.difficulty, "conf": label.confidence,
                "reason": label.reasoning,
            })
            print(f"    → {label.skill_id} | сложность {label.difficulty:.2f}")
            count += 1

        return count


def relabel_all() -> int:
    """Удаляет все авторазметки и размечает заново."""
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM task_labels WHERE model = 'gigachat'"))
    return label_unlabeled()


# ─── CLI ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Импорт заданий в HyperUm")
    parser.add_argument("csv", nargs="?", help="Путь к CSV с заданиями")
    parser.add_argument("--import-only", action="store_true",
                        help="Только импорт, без разметки")
    parser.add_argument("--relabel", action="store_true",
                        help="Переразметить все задания")
    args = parser.parse_args()

    if args.relabel:
        print("=== Переразметка всех заданий ===")
        count = relabel_all()
        print(f"\nРазмечено: {count}")
        return

    if not args.csv:
        parser.print_help()
        sys.exit(1)

    if not Path(args.csv).exists():
        print(f"Файл не найден: {args.csv}")
        sys.exit(1)

    print(f"=== Импорт из {args.csv} ===")
    created, updated = import_csv(args.csv)
    print(f"\nСоздано: {created}, обновлено: {updated}")

    if args.import_only:
        print("Разметка пропущена (--import-only).")
        return

    print("\n=== Разметка через GigaChat ===")
    labeled = label_unlabeled()
    print(f"\nРазмечено: {labeled}")

    print("\n=== Готово ===")


if __name__ == "__main__":
    main()