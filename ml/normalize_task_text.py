"""
Нормализация текста заданий.

Задача: найти LaTeX-фрагменты без обёртки, обернуть их в $...$,
удалить plain-дубли вокруг.

Пример:
    было:  F ( n ) = n ⋅ n + 11 F(n) = n \cdot n + 11 F ( n ) = n ⋅ n + 11
    стало: $F(n) = n \cdot n + 11$

Использование:
    python -m ml.normalize_task_text --dry-run        # посмотреть
    python -m ml.normalize_task_text --apply          # применить
    python -m ml.normalize_task_text --apply --code task_953  # одно задание
"""
import argparse
import os
import re
import sys
from dataclasses import dataclass

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_URL = os.getenv("HYPERUM_DB_URL")

# ─── LaTeX-команды-маркеры ────────────────────────────────
# Если фрагмент содержит хотя бы одну из них — это LaTeX.
LATEX_COMMANDS = [
    r'\cdot', r'\times', r'\div', r'\pm', r'\mp',
    r'\leq', r'\geq', r'\le', r'\ge', r'\neq', r'\ne',
    r'\leqslant', r'\geqslant',
    r'\begin{cases}', r'\end{cases}', r'\text{', r'\%',
    r'\frac', r'\sqrt', r'\in', r'\subset', r'\to',
]

# Regex: хотя бы одна команда из списка
LATEX_MARKER_RE = re.compile('|'.join(re.escape(c) for c in LATEX_COMMANDS))


# ─── Утилиты ──────────────────────────────────────────────

def normalize_for_compare(s: str) -> str:
    """
    Приводит строку к каноническому виду для сравнения:
    - удаляет пробелы
    - \cdot → ⋅, \times → ×, \leq → ≤, \geq → ≥ и т.д.
    """
    result = s
    result = result.replace('\\cdot', '⋅')
    result = result.replace('\\times', '×')
    result = result.replace('\\div', '÷')
    result = result.replace('\\leq', '≤')
    result = result.replace('\\geq', '≥')
    result = result.replace('\\le', '≤')
    result = result.replace('\\ge', '≥')
    result = result.replace('\\neq', '≠')
    result = result.replace('\\ne', '≠')
    result = result.replace('\\leqslant', '⩽')
    result = result.replace('\\geqslant', '⩾')
    result = result.replace('\\pm', '±')
    result = result.replace('\\mp', '∓')
    result = result.replace('\\%', '%')
    result = result.replace('\\ ', '')
    # Удаляем все пробелы (включая неразрывные)
    result = re.sub(r'\s+', '', result)
    return result


def contains_latex(s: str) -> bool:
    """Есть ли в строке LaTeX-команда."""
    return bool(LATEX_MARKER_RE.search(s))


# ─── Основная логика нормализации ─────────────────────────

def find_latex_spans(text: str) -> list[tuple[int, int, str]]:
    """
    Находит фрагменты текста, содержащие LaTeX-команды.
    Возвращает [(start, end, fragment), ...].
    Границы: пробел или знаки препинания.
    """
    # Проходим по тексту, ищем слова/фрагменты, содержащие \commands
    spans = []
    # Разбиваем по границам предложений, но сохраняем позиции
    # Ищем фрагменты, где встречаются \something

    # Найдём все позиции LaTeX-команд
    for match in re.finditer(r'\\[a-zA-Z]+', text):
        start_cmd = match.start()
        end_cmd = match.end()

        # Расширяем влево: до пробела, знаков препинания, или слова
        left = start_cmd
        while left > 0 and text[left - 1] not in ' \t\n':
            # Останавливаемся на знаках, которые обычно разделяют фразы
            if text[left - 1] in ';,.':
                break
            left -= 1

        # Расширяем вправо: до пробела или разделителя
        right = end_cmd
        # Продолжаем, пока не пробел/разделитель
        # Но учитываем, что LaTeX может содержать { ... } с пробелами
        brace_depth = 0
        while right < len(text):
            ch = text[right]
            if ch == '{':
                brace_depth += 1
            elif ch == '}':
                brace_depth -= 1
            elif ch in ' \t\n' and brace_depth == 0:
                # Смотрим дальше — если следующее слово тоже часть формулы?
                # (например "n \cdot n + 11" — после n идёт пробел и ещё n)
                # Если следующее слово начинается с буквы/цифры или \, продолжаем
                # НО если следующее слово — это "при", "если", "и", останавливаемся
                lookahead = text[right + 1:right + 20].strip()
                if lookahead.startswith('при') or \
                   lookahead.startswith('если') or \
                   lookahead.startswith('когда') or \
                   lookahead.startswith('и '):
                    break
                # Останавливаемся также на ;, . (если это конец фразы)
            if ch == ';' or ch == '.':
                # Если это конец предложения — стоп
                break
            right += 1

        spans.append((left, right, text[left:right]))

    # Склеиваем пересекающиеся/близкие спаны
    spans.sort()
    merged = []
    for span in spans:
        if merged and span[0] <= merged[-1][1] + 5:
            # Близко — объединяем
            merged[-1] = (merged[-1][0], span[1], text[merged[-1][0]:span[1]])
        else:
            merged.append(list(span))
    return [tuple(s) for s in merged]


def find_duplicates_around(
    text: str, latex_span: tuple[int, int, str]
) -> list[tuple[int, int]]:
    """
    Ищет plain-дубли вокруг LaTeX-фрагмента.
    Возвращает список [(start, end), ...] для удаления.
    """
    start, end, latex_fragment = latex_span
    latex_norm = normalize_for_compare(latex_fragment)

    duplicates = []

    # Ищем дубли слева (в пределах 400 символов)
    left_zone = text[max(0, start - 400):start]
    # Ищем фрагменты, нормализованные которых равны latex_norm
    # Разбиваем на "фразы" — от пробела до пробела + учёт юникода
    for m in re.finditer(r'[^\s]{2,}', left_zone):
        candidate = m.group()
        # Пробуем расширить фрагмент: склеиваем соседние слова
        # (например, "F ( n )" — это отдельные слова)
        # Сложно — вместо этого ищем совпадения нормализованных
        candidate_norm = normalize_for_compare(candidate)
        if candidate_norm and candidate_norm in latex_norm:
            # Частичное совпадение — пропускаем, ищем целое
            continue
        if candidate_norm == latex_norm:
            abs_start = max(0, start - 400) + m.start()
            duplicates.append((abs_start, abs_start + len(candidate)))

    # Ищем дубли справа
    right_zone = text[end:end + 400]
    for m in re.finditer(r'[^\s]{2,}', right_zone):
        candidate = m.group()
        candidate_norm = normalize_for_compare(candidate)
        if candidate_norm == latex_norm:
            abs_start = end + m.start()
            duplicates.append((abs_start, abs_start + len(candidate)))

    return duplicates


def normalize_text(original: str) -> tuple[str, bool]:
    """
    Нормализует текст задания.
    Возвращает (новый_текст, изменилось_ли).
    """
    text = original
    spans = find_latex_spans(text)

    if not spans:
        return original, False

    # Идём с конца, чтобы индексы не сдвигались
    for span in reversed(spans):
        start, end, fragment = span
        latex_norm = normalize_for_compare(fragment)

        # Обернуть фрагмент в $...$ (или $$ ... $$ для cases)
        if '\\begin{cases}' in fragment:
            wrapped = f"$$ {fragment} $$"
        else:
            wrapped = f"${fragment}$"

        # Найти дубли
        dups = find_duplicates_around(text, span)

        # Удалить дубли (с конца)
        for d_start, d_end in sorted(dups, reverse=True):
            text = text[:d_start] + text[d_end:]

        # Заменить LaTeX на обёрнутый
        # Индексы сдвинулись — пересчитать
        # Проще: заменить fragment как подстроку (уникальный)
        text = text.replace(fragment, wrapped, 1)

    # Схлопнуть множественные пробелы
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\s+([;,.])', r'\1', text)

    return text, text != original


# ─── Основной цикл ─────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true',
                        help='Показать изменения, но не сохранять')
    parser.add_argument('--apply', action='store_true',
                        help='Применить изменения')
    parser.add_argument('--code', type=str, default=None,
                        help='Обработать только одно задание')
    parser.add_argument('--limit', type=int, default=None,
                        help='Ограничить число заданий')
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Укажи --dry-run или --apply")
        sys.exit(1)

    engine = create_engine(DB_URL)

    with engine.connect() as conn:
        where = "WHERE code = :code" if args.code else ""
        params = {"code": args.code} if args.code else {}
        limit = f"LIMIT {args.limit}" if args.limit else ""

        rows = conn.execute(text(f"""
            SELECT id, code, text FROM tasks
            {where}
            ORDER BY code
            {limit}
        """), params).fetchall()

    print(f"Найдено заданий: {len(rows)}\n")

    changed = 0
    for row in rows:
        task_id, code, original = row
        new_text, did_change = normalize_text(original)

        if did_change:
            changed += 1
            if args.dry_run:
                print(f"─── {code} ───")
                print(f"БЫЛО:  {original[:200]}")
                print(f"СТАЛО: {new_text[:200]}")
                print()
            elif args.apply:
                with engine.begin() as conn:
                    conn.execute(text("""
                        UPDATE tasks SET text = :t WHERE id = :id
                    """), {"t": new_text, "id": task_id})
                print(f"✓ {code}")

    print(f"\nИтого: изменено {changed} из {len(rows)}")


if __name__ == "__main__":
    main()