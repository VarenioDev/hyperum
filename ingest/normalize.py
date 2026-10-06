"""
Единая логика нормализации и сравнения ответов.
Все сравнения в системе ДОЛЖНЫ идти через эту функцию.
"""
import re
from typing import Any


def to_str(v: Any) -> str:
    """Приводит любое значение к строке, убирая артефакты pandas/numpy."""
    if v is None:
        return ""

    # pandas NaN / None
    try:
        import pandas as pd
        if pd.isna(v):
            return ""
    except (ImportError, TypeError, ValueError):
        pass

    # числовые типы: 21.0 -> "21", 21.5 -> "21.5"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v.is_integer():
            return str(int(v))
        return repr(v)

    return str(v)


def normalize_text(s: Any) -> str:
    """
    Нормализует ответ для сравнения:
    - trim, lower
    - NBSP -> пробел
    - множественные пробелы -> один
    - запятая -> точка (десятичный разделитель)
    - хвостовые нули: "21.0" -> "21", "3.140" -> "3.14"
    - хвостовая точка: "21." -> "21"
    """
    s = to_str(s)
    s = s.replace("\u00a0", " ").strip().lower()
    if not s:
        return ""

    s = re.sub(r"\s+", " ", s)
    s = s.replace(",", ".")

    if re.fullmatch(r"-?\d+\.", s):
        s = s[:-1]
    elif re.fullmatch(r"-?\d+\.0+", s):
        s = s.split(".")[0]
    elif re.fullmatch(r"-?\d+\.\d*[1-9]0+", s):
        s = s.rstrip("0").rstrip(".")

    return s


def normalize_multi(s: Any) -> frozenset[str]:
    """Множественный выбор: 'a; b, c' -> {'a','b','c'}."""
    s = normalize_text(s)
    if not s:
        return frozenset()
    parts = re.split(r"[;,]", s)
    return frozenset(p.strip() for p in parts if p.strip())


def answers_equal(student: Any, expected: Any, task_type: str = "text") -> bool:
    """Главная функция сравнения. Используй только её."""
    if task_type == "multi_choice":
        return normalize_multi(student) == normalize_multi(expected)
    return normalize_text(student) == normalize_text(expected)