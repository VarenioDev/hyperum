"""
Автоматическая разметка заданий через DeepSeek API.
Multi-skill (primary + 0-2 secondary) + батчинг.

Использование:
    python -m ml.label_tasks_with_deepseek
"""
import json
import os
import re
import time
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import create_engine, text

load_dotenv()

DB_URL = os.getenv("HYPERUM_DB_URL")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("Не задан DEEPSEEK_API_KEY в .env")

API_URL = "https://api.deepseek.com/chat/completions"
MODEL_API = "deepseek-chat"
MODEL_TAG = "deepseek"

# ─── Параметры батчинга ─────────────────────────────────────
BATCH_SIZE = 10                 # заданий за один запрос
MAX_RETRIES = 2                 # попыток на батч
SLEEP_BETWEEN_BATCHES = 0.5     # сек между запросами
SLEEP_BETWEEN_RETRIES = 2.0     # сек между retry

engine = create_engine(DB_URL)


# ─── Схемы ответа ──────────────────────────────────────────

class BatchTaskLabel(BaseModel):
    task_code: str
    primary_skill: str
    secondary_skills: list[str] = Field(default_factory=list)
    difficulty: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""


class BatchResponse(BaseModel):
    labels: list[BatchTaskLabel]


# ─── Таксономия ────────────────────────────────────────────

def load_taxonomy_text() -> str:
    tax_path = Path(__file__).parent.parent / "taxonomy" / "informatics_10_11.yaml"
    if not tax_path.exists():
        tax_path = Path(__file__).parent.parent / "taxonomy" / "informatics_10.yaml"

    with open(tax_path, encoding="utf-8") as f:
        taxonomy = yaml.safe_load(f)

    lines = []
    for module in taxonomy:
        for topic in module.get("topics", []):
            for skill in topic.get("skills", []):
                lines.append(
                    f'- ID: "{skill["id"]}" | '
                    f'Название: "{skill["name"]}" | '
                    f'Сложность по умолчанию: {skill.get("difficulty", 0.5)}'
                )
    return "\n".join(lines)


# ─── Промпт ────────────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """Ты — опытный методист по информатике с 20-летним стажем. Твоя задача — разметить несколько школьных заданий одновременно.

═══════════════════════════════════════════════════════════════
ЗАДАЧА
═══════════════════════════════════════════════════════════════

Ты получишь список заданий с их кодами. Разметь КАЖДОЕ.

Для каждого задания верни объект:
{{
  "task_code": "точный код задания из входа",
  "primary_skill": "s_xxx",
  "secondary_skills": ["s_yyy"],
  "difficulty": 0.XX,
  "confidence": 0.XX,
  "reasoning": "1) главный навык, 2) вторичные, 3) почему такая сложность"
}}

Ответ должен быть JSON-объектом с полем "labels" — массив всех размеченных заданий:
{{ "labels": [ {{...}}, {{...}}, ... ] }}

Количество элементов в "labels" ДОЛЖНО точно совпадать с количеством заданий во входе.

═══════════════════════════════════════════════════════════════
ПРАВИЛА МУЛЬТИ-НАВЫКОВ
═══════════════════════════════════════════════════════════════

• primary_skill — навык, который проверяется В ПЕРВУЮ ОЧЕРЕДЬ. Ровно один.
• secondary_skills — навыки, которые ТОЖЕ задействованы, но не главные. От 0 до 2. Пустой массив [], если нет.
• Не дублируй primary_skill в secondary_skills.
• Если задание проверяет один навык — secondary_skills = [].
• Если задание требует комбинации из двух-трёх навыков — один в primary, остальные в secondary.

═══════════════════════════════════════════════════════════════
РУБРИКА СЛОЖНОСТИ (0.0 – 1.0)
═══════════════════════════════════════════════════════════════

• 0.0–0.2 (очень легко): одно действие, воспроизведение, 30 сек.
• 0.2–0.4 (легко): одно действие с пониманием, 1–2 шага, 1 минута.
• 0.4–0.6 (средне): 2–3 шага, комбинирование 1–2 понятий, 2–3 минуты.
• 0.6–0.8 (сложно): 3–4 шага, ловушки, 3–5 минут, часто ошибаются.
• 0.8–1.0 (очень сложно): многошаговое, неочевидная стратегия, олимпиадный уровень.

Сложность — это НЕ длина условия. Длинная задача с одним действием — лёгкая.

═══════════════════════════════════════════════════════════════
ЭТАЛОНЫ (для калибровки)
═══════════════════════════════════════════════════════════════

── ЭТАЛОН 1: ЛЁГКОЕ, один навык ──
Задание (task_ex1): "Сколько бит в 4 байтах?"
Ответ: {{"task_code": "task_ex1", "primary_skill": "s_units", "secondary_skills": [], "difficulty": 0.21, "confidence": 0.95, "reasoning": "1) Перевод единиц. 2) Вторичных нет. 3) Одно действие."}}

── ЭТАЛОН 2: СРЕДНЕЕ, один навык ──
Задание (task_ex2): "Переведите число 255 из десятичной системы в шестнадцатеричную."
Ответ: {{"task_code": "task_ex2", "primary_skill": "s_dec_to_base", "secondary_skills": [], "difficulty": 0.47, "confidence": 0.9, "reasoning": "1) Перевод из 10-й в 16-ю СС. 2) Вторичных нет. 3) Два шага."}}

── ЭТАЛОН 3: СЛОЖНОЕ, два навыка ──
Задание (task_ex3): "Напишите программу, которая выводит таблицу умножения на 7 с помощью вложенных циклов."
Ответ: {{"task_code": "task_ex3", "primary_skill": "s_nested", "secondary_skills": ["s_for"], "difficulty": 0.78, "confidence": 0.85, "reasoning": "1) Главное — вложенные циклы. 2) Требуется понимание обычного for. 3) Комбинация двух навыков."}}

═══════════════════════════════════════════════════════════════
ТАКСОНОМИЯ (список доступных навыков)
═══════════════════════════════════════════════════════════════

{taxonomy}

═══════════════════════════════════════════════════════════════
ПРАВИЛА
═══════════════════════════════════════════════════════════════

1. primary_skill и secondary_skills — только из списка выше.
2. difficulty — [0.0, 1.0], два знака после запятой.
3. confidence — 0.9+ если очевидно, 0.5 если сомневаешься.
4. task_code — ТОЧНО как во входе (не придумывай, не меняй).
5. Твой шаг в оценке сложности - 0.01; чем точнее будет оценка - тем лучше
6. Отвечай ТОЛЬКО JSON, без markdown-обёрток.
"""


def build_system_prompt() -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(taxonomy=load_taxonomy_text())


# ─── Запрос к LLM ──────────────────────────────────────────

def parse_json_response(raw: str) -> dict | None:
    """Достаёт JSON из ответа модели, даже если он обёрнут в ```json ... ```."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
        return None


def call_deepseek(system_prompt: str, user_content: str) -> dict | None:
    """Один HTTP-запрос к DeepSeek. Возвращает распарсенный JSON или None."""
    try:
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL_API,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            },
            timeout=180,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return parse_json_response(content)
    except requests.HTTPError as e:
        print(f"    HTTP ошибка: {e} — {response.text[:200]}")
        return None
    except Exception as e:
        print(f"    Ошибка: {e}")
        return None


# ─── Разметка батча ────────────────────────────────────────

def format_batch_for_prompt(batch: list[dict]) -> str:
    lines = ["Разметь следующие задания:\n"]
    for i, task in enumerate(batch, 1):
        lines.append(f"─── Задание {i} ───")
        lines.append(f"Код: {task['code']}")
        lines.append(f"Текст: {task['text']}")
        lines.append("")
    return "\n".join(lines)


def label_batch(batch: list[dict]) -> dict[str, BatchTaskLabel]:
    """
    Размечает батч заданий. Возвращает dict {task_code: BatchTaskLabel}.
    Пустой dict — если не удалось.
    """
    system_prompt = build_system_prompt()
    user_content = format_batch_for_prompt(batch)
    expected_codes = {t["code"] for t in batch}

    for attempt in range(MAX_RETRIES + 1):
        data = call_deepseek(system_prompt, user_content)
        if not data:
            if attempt < MAX_RETRIES:
                time.sleep(SLEEP_BETWEEN_RETRIES)
            continue

        try:
            parsed = BatchResponse.model_validate(data)
        except ValidationError as e:
            print(f"    Валидация не прошла (попытка {attempt + 1}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(SLEEP_BETWEEN_RETRIES)
            continue

        returned_codes = {lbl.task_code for lbl in parsed.labels}

        # Проверяем, что коды совпадают
        if returned_codes != expected_codes:
            missing = expected_codes - returned_codes
            extra = returned_codes - expected_codes
            print(f"    Несовпадение кодов (попытка {attempt + 1}): "
                  f"missing={missing}, extra={extra}")
            if attempt < MAX_RETRIES:
                time.sleep(SLEEP_BETWEEN_RETRIES)
            continue

        return {lbl.task_code: lbl for lbl in parsed.labels}

    return {}


def label_single(task: dict) -> BatchTaskLabel | None:
    """Fallback: разметка одного задания, если батч не сработал."""
    system_prompt = build_system_prompt()
    user_content = format_batch_for_prompt([task])

    data = call_deepseek(system_prompt, user_content)
    if not data:
        return None
    try:
        parsed = BatchResponse.model_validate(data)
        if parsed.labels:
            return parsed.labels[0]
    except ValidationError:
        pass
    return None


# ─── Сохранение в БД ───────────────────────────────────────

def save_label(conn, task_id: str, label: BatchTaskLabel) -> None:
    """Сохраняет primary-навык и secondary-навыки для задания."""
    # Primary
    conn.execute(text("""
        INSERT INTO task_labels
            (task_id, skill_id, difficulty, confidence, model, reasoning, is_primary)
        VALUES (:tid, :sid, :diff, :conf, :model, :reason, TRUE)
        ON CONFLICT (task_id, skill_id, model) DO UPDATE
          SET difficulty = EXCLUDED.difficulty,
              confidence = EXCLUDED.confidence,
              reasoning = EXCLUDED.reasoning,
              is_primary = TRUE
    """), {
        "tid": task_id, "sid": label.primary_skill,
        "diff": label.difficulty, "conf": label.confidence,
        "model": MODEL_TAG, "reason": label.reasoning,
    })

    # Secondary (до 2, без дублирования primary)
    for sec in label.secondary_skills[:2]:
        if sec == label.primary_skill:
            continue
        conn.execute(text("""
            INSERT INTO task_labels
                (task_id, skill_id, difficulty, confidence, model, reasoning, is_primary)
            VALUES (:tid, :sid, :diff, :conf, :model, :reason, FALSE)
            ON CONFLICT (task_id, skill_id, model) DO UPDATE
              SET difficulty = EXCLUDED.difficulty,
                  confidence = EXCLUDED.confidence,
                  reasoning = EXCLUDED.reasoning,
                  is_primary = FALSE
        """), {
            "tid": task_id, "sid": sec,
            "diff": label.difficulty, "conf": label.confidence,
            "model": MODEL_TAG, "reason": label.reasoning,
        })


# ─── Основной цикл ─────────────────────────────────────────

def main():
    with engine.begin() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM tasks")).scalar()
        already = conn.execute(text(
            "SELECT COUNT(DISTINCT task_id) FROM task_labels WHERE model = :m"
        ), {"m": MODEL_TAG}).scalar()
        print(f"Всего заданий: {total}")
        print(f"Уже размечено DeepSeek: {already}\n")

        tasks = conn.execute(text("""
            SELECT t.id, t.code, t.text
            FROM tasks t
            LEFT JOIN task_labels tl
              ON tl.task_id = t.id AND tl.model = :m
            WHERE tl.task_id IS NULL
            ORDER BY t.code
        """), {"m": MODEL_TAG}).fetchall()

        if not tasks:
            print("Все задания уже размечены.")
            return

        tasks = [{"id": str(r[0]), "code": r[1], "text": r[2]} for r in tasks]
        n_tasks = len(tasks)
        n_batches = (n_tasks + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"К разметке: {n_tasks} заданий, {n_batches} батчей по {BATCH_SIZE}\n")

        success = 0
        fallback = 0
        failed = 0

        for b_idx in range(n_batches):
            batch = tasks[b_idx * BATCH_SIZE:(b_idx + 1) * BATCH_SIZE]
            print(f"─── Батч {b_idx + 1}/{n_batches} "
                  f"({len(batch)} заданий) ───")

            labels = label_batch(batch)

            if len(labels) == len(batch):
                for task in batch:
                    save_label(conn, task["id"], labels[task["code"]])
                    print(f"    ✓ {task['code']} → "
                          f"{labels[task['code']].primary_skill} "
                          f"(+{len(labels[task['code']].secondary_skills)} sec)")
                    success += 1
            else:
                # Fallback: размечаем по одному
                print(f"    Fallback: размечаем по одному")
                for task in batch:
                    label = label_single(task)
                    if label:
                        save_label(conn, task["id"], label)
                        print(f"    ✓ {task['code']} → {label.primary_skill} "
                              f"(single)")
                        success += 1
                        fallback += 1
                    else:
                        print(f"    ✗ {task['code']} — не удалось")
                        failed += 1

            # Пауза между батчами
            if b_idx < n_batches - 1:
                time.sleep(SLEEP_BETWEEN_BATCHES)

    print(f"\n═══ Итог ═══")
    print(f"Успешно: {success}/{n_tasks}")
    print(f"  из них через fallback: {fallback}")
    print(f"Не удалось: {failed}")


if __name__ == "__main__":
    main()