"""
Percentile-нормализация сложностей.
Переводит raw-оценки LLM в равномерное распределение [0.15, 0.9].

Проблема: LLM кластеризует сложности в узком диапазоне (0.6–0.7).
Решение: percentile-based — сортируем по raw, раздаём новые
значения по равномерной шкале.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import numpy as np

load_dotenv()

DB_URL = os.getenv("HYPERUM_DB_URL")
MODEL = "deepseek"  # какую модель нормализуем

engine = create_engine(DB_URL)


def percentile_normalize(values: list[float], low=0.15, high=0.90) -> list[float]:
    """
    Перевести список значений в равномерную шкалу [low, high] по рангам.
    Одинаковые значения получат одинаковый новый ранг.
    """
    arr = np.array(values)
    # Ранг: 0 для минимума, 1 для максимума
    ranks = arr.argsort().argsort() / max(len(arr) - 1, 1)
    normalized = low + ranks * (high - low)
    return normalized.tolist()


def main():
    with engine.begin() as conn:
        # Читаем сырые сложности
        rows = conn.execute(text("""
            SELECT task_id, difficulty
            FROM task_labels
            WHERE model = :m
            ORDER BY task_id
        """), {"m": MODEL}).fetchall()

        if not rows:
            print("Нет данных для нормализации.")
            return

        task_ids = [r[0] for r in rows]
        raw_values = [float(r[1]) for r in rows]

        print(f"Заданий: {len(rows)}")
        print(f"Было: min={min(raw_values):.2f}, max={max(raw_values):.2f}, "
              f"avg={sum(raw_values)/len(raw_values):.2f}")

        # Нормализуем
        normalized = percentile_normalize(raw_values)

        print(f"Стало: min={min(normalized):.2f}, max={max(normalized):.2f}, "
              f"avg={sum(normalized)/len(normalized):.2f}")

        # Обновляем
        updated = 0
        for task_id, new_diff in zip(task_ids, normalized):
            conn.execute(text("""
                UPDATE task_labels
                SET difficulty = :d
                WHERE task_id = :tid AND model = :m
            """), {
                "d": round(new_diff, 3),
                "tid": task_id, "m": MODEL,
            })
            updated += 1

    print(f"\nОбновлено: {updated} записей")


if __name__ == "__main__":
    main()