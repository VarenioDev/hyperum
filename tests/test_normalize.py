"""
Проверка логики сравнения ответов.
Запуск: python tests/test_normalize.py
"""
from ingest.normalize import normalize_text, normalize_multi, answers_equal


CASES = [
    # (student, expected, type, should_be_correct, комментарий)
    ("21",    "21",    "text", True,  "точное совпадение"),
    ("21.0",  "21",    "text", True,  "float из pandas -> int"),
    ("21.",   "21",    "text", True,  "хвостовая точка"),
    (" 21 ",  "21",    "text", True,  "лишние пробелы"),
    ("21",    "21.0",  "text", True,  "expected тоже float"),
    ("21,0",  "21",    "text", True,  "запятая как разделитель"),
    ("3.140", "3.14",  "text", True,  "хвостовые нули"),
    ("FF",    "ff",    "text", True,  "регистр"),
    ("ff",    "FF",    "text", True,  "регистр обратно"),
    ("0 1 2", "0 1 2", "text", True,  "пробелы внутри"),
    ("0  1  2", "0 1 2", "text", True, "двойные пробелы"),
    ("21",    "22",    "text", False, "действительно разные"),
    ("21.5",  "21",    "text", False, "дробное vs целое"),
    ("",      "21",    "text", False, "пустой ответ"),
    # множественный выбор
    ("a;b;c", "c;b;a", "multi_choice", True,  "порядок не важен"),
    ("a, b, c", "c;b;a", "multi_choice", True, "разные разделители"),
    ("a;b",   "a;b;c", "multi_choice", False, "разные множества"),
]


def main():
    failed = 0
    for student, expected, ttype, want, comment in CASES:
        got = answers_equal(student, expected, ttype)
        mark = "OK " if got == want else "FAIL"
        if got != want:
            failed += 1
        print(f"[{mark}] {comment:<30} | {student!r} vs {expected!r} -> {got}")

    if failed:
        print(f"\nПровалено: {failed}")
        raise SystemExit(1)
    print(f"\nВсе {len(CASES)} тестов прошли.")


if __name__ == "__main__":
    main()