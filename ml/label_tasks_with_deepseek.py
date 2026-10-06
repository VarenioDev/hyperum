"""
Автоматическая разметка заданий через DeepSeek API (HTTP, без SDK).
"""
import json
import os
import re
from pathlib import Path
import requests
import yaml
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_URL = os.getenv("HYPERUM_DB_URL")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("Не задан DEEPSEEK_API_KEY в .env")

API_URL = "https://api.deepseek.com/chat/completions"
MODEL_API = "deepseek-chat"
MODEL_TAG = "deepseek"

engine = create_engine(DB_URL)


# ─── Загрузка таксономии ─────────────────────────────────────

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
                    f'Базовая сложность: {skill.get("difficulty", 0.5)}'
                )
    return "\n".join(lines)


# ─── Промпт (тот же, что для GigaChat) ───────────────────────

SYSTEM_PROMPT_TEMPLATE = """
Ты — опытный методист по информатике с 20-летним стажем. Твоя задача — разметить школьное задание по двум параметрам: навык (skill_id) и сложность (difficulty от 0.0 до 1.0).

═══════════════════════════════════════════════════════════════
ЗАДАЧА
═══════════════════════════════════════════════════════════════

Для каждого задания верни JSON строго следующей структуры:

{{
  "skill_id": "s_xxx",
  "difficulty": 0.XX,
  "confidence": 0.XX,
  "reasoning": "Пошаговое объяснение: 1) какой навык проверяется, 2) какие шаги нужны для решения, 3) почему такая оценка сложности."
}}

Никаких пояснений вне JSON. Только валидный JSON-объект.

═══════════════════════════════════════════════════════════════
РУБРИКА СЛОЖНОСТИ (шкала 0.0 – 1.0)
═══════════════════════════════════════════════════════════════

Оценивай по количеству шагов и типу мышления. Твой шаг - 0.01, старайся использовать как можно более точную оценку и не стесняйся использовать оценку до сотой доли

• 0.01 – 0.20 (очень легко): Задание на воспроизведение. Одно действие, одна формула, прямой подстановкой. Ученик 10 класса решает за 30 секунд без размышлений.

• 0.21 – 0.40 (легко): Одно действие, но требует понимания концепции. Одна формула + подстановка. 1–2 шага. Ученик решает за 1 минуту.

• 0.41 – 0.60 (средне): 2–3 шага, комбинирование 1–2 понятий. Требуется выбрать правильный метод. Ученик решает за 2–3 минуты.

• 0.61 – 0.80 (сложно): 3–4 шага, комбинирование нескольких понятий. Возможны ловушки (единицы измерения, порядок действий). Ученик решает за 3–5 минут, часто ошибается.

• 0.81 – 1.0 (очень сложно): Многошаговое решение с неочевидной стратегией. Требует глубокого понимания или комбинации 3+ навыков. Олимпиадный уровень.

ВАЖНО: сложность — это НЕ длина условия. Длинная задача с одним действием — лёгкая. Короткая задача с несколькими шагами — сложная.

═══════════════════════════════════════════════════════════════
ЭТАЛОННЫЕ ПРИМЕРЫ (для калибровки)
═══════════════════════════════════════════════════════════════

Используй эти три примера как точку отсчёта.

── ЭТАЛОН 1: ЛЁГКОЕ (difficulty = 0.18) ──
Задание: "Сколько бит в 4 байтах?"
Ответ:
{{
  "skill_id": "s_volume",
  "difficulty": 0.18,
  "confidence": 0.95,
  "reasoning": "1) Проверяется навык перевода единиц измерения информации (байты → биты). 2) Одно действие: 4 × 8 = 32. 3) Сложность 0.2 — ученик знает формулу и применяет её напрямую."
}}

── ЭТАЛОН 2: СРЕДНЕЕ (difficulty = 0.49) ──
Задание: "Переведите число 255 из десятичной системы счисления в шестнадцатеричную."
Ответ:
{{
  "skill_id": "s_dec_to_base",
  "difficulty": 0.49,
  "confidence": 0.9,
  "reasoning": "1) Проверяется навык перевода из 10-й в 16-ю СС. 2) Два шага: деление на 16, запись остатков в обратном порядке. 3) Сложность 0.5 — ученик знает метод, но должен аккуратно выполнить деление и не перепутать порядок."
}}

── ЭТАЛОН 3: СЛОЖНОЕ (difficulty = 0.77) ──
Задание: "По каналу связи передаются сообщения из четырёх букв: А, Б, В, Г. Используется двоичный код, удовлетворяющий условию Фано. Для А, Б, В используются кодовые слова 0, 10, 110. Укажите кратчайшее кодовое слово для Г."
Ответ:
{{
  "skill_id": "s_fano_direct",
  "difficulty": 0.77,
  "confidence": 0.85,
  "reasoning": "1) Проверяется понимание прямого условия Фано. 2) Три шага: проверить, что ни одно кодовое слово не является префиксом другого, найти свободную ветку, выбрать кратчайший код. 3) Сложность 0.75 — ученик должен понимать структуру префиксного дерева, что даётся не всем."
}}

Используй эти примеры как камертон. Если задание сложнее эталона 2, но проще эталона 3 — ставь 0.6–0.7.

═══════════════════════════════════════════════════════════════
ТАКСОНОМИЯ (список доступных навыков)
═══════════════════════════════════════════════════════════════

Выбери РОВНО ОДИН skill_id из этого списка. Не придумывай новые.

{taxonomy}

═══════════════════════════════════════════════════════════════
ПРАВИЛА
═══════════════════════════════════════════════════════════════

1. skill_id — только из списка выше. Если ни один не подходит идеально, выбери ближайший.
2. difficulty — обязательно в диапазоне [0.0, 1.0], с двумя знаками после запятой.
3. confidence — насколько ты уверен: 0.9+ если очевидно, 0.5 если сомневаешься.
4. reasoning — ОБЯЗАТЕЛЬНО по шагам (1, 2, 3), как в эталонах.
5. Не добавляй поля сверх указанных.
6. Отвечай ТОЛЬКО JSON, без markdown-обёрток.
7. Твой шаг в оценке сложности - 0.01; чем точнее ты оценишь - тем лучше!
"""


def build_system_prompt() -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(taxonomy=load_taxonomy_text())


# ─── Разметка одного задания ─────────────────────────────────

def parse_json_response(raw: str) -> dict | None:
    """Достаёт JSON из ответа модели, даже если он обёрнут в ```json ... ```."""
    raw = raw.strip()
    # Снять markdown-обёртку
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Попробовать найти JSON-объект в тексте
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
        return None


def label_task(task_text: str) -> dict | None:
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
                    {"role": "system", "content": build_system_prompt()},
                    {"role": "user", "content": f"Разметь задание:\n\n{task_text}"},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            },
            timeout=120,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        data = parse_json_response(content)
        if data is None:
            return None

        # Валидация полей
        skill_id = str(data.get("skill_id", "")).strip()
        difficulty = float(data.get("difficulty", 0.5))
        confidence = float(data.get("confidence", 0.5))
        reasoning = str(data.get("reasoning", ""))

        if not skill_id or not (0.0 <= difficulty <= 1.0):
            return None

        return {
            "skill_id": skill_id,
            "difficulty": round(difficulty, 2),
            "confidence": round(confidence, 2),
            "reasoning": reasoning,
        }
    except requests.HTTPError as e:
        print(f"    HTTP ошибка: {e} — {response.text[:200]}")
        return None
    except Exception as e:
        print(f"    Ошибка: {e}")
        return None


# ─── Основной цикл ───────────────────────────────────────────

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
            print("Все задания уже размечены DeepSeek.")
            return

        print(f"К разметке: {len(tasks)}\n")

        success = 0
        for i, (task_id, code, task_text) in enumerate(tasks, 1):
            print(f"[{i}/{len(tasks)}] {code}")
            label = label_task(task_text)

            if label:
                conn.execute(text("""
                    INSERT INTO task_labels
                        (task_id, skill_id, difficulty, confidence, model, reasoning)
                    VALUES (:tid, :sid, :diff, :conf, :model, :reason)
                    ON CONFLICT (task_id, skill_id, model) DO UPDATE
                      SET difficulty = EXCLUDED.difficulty,
                          confidence = EXCLUDED.confidence,
                          reasoning = EXCLUDED.reasoning
                """), {
                    "tid": task_id, "sid": label["skill_id"],
                    "diff": label["difficulty"], "conf": label["confidence"],
                    "model": MODEL_TAG, "reason": label["reasoning"],
                })
                print(f"    → {label['skill_id']} | {label['difficulty']:.2f} | "
                      f"conf {label['confidence']:.2f}")
                success += 1
            else:
                print("    → не удалось")

        print(f"\nУспешно: {success}/{len(tasks)}")


if __name__ == "__main__":
    main()