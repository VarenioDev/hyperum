"""
Автоматическая разметка заданий через GigaChat API.
"""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from pydantic import BaseModel, Field
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

# Загружаем переменные окружения
load_dotenv()

DB_URL = os.getenv("HYPERUM_DB_URL")
GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY")
if not GIGACHAT_AUTH_KEY:
    raise ValueError("Не задан GIGACHAT_AUTH_KEY в .env")

# Инициализируем клиент GigaChat
# Scope "GIGACHAT_API_PERS" указывает, что мы используем доступ для физлиц
client = GigaChat(credentials=GIGACHAT_AUTH_KEY, scope="GIGACHAT_API_PERS", verify_ssl_certs=False)

# Модель. GigaChat-2-Pro или GigaChat-2-Max — хороший выбор для сложных задач.
MODEL = "GigaChat-2-Pro"

engine = create_engine(DB_URL)

# --- Схема ответа от LLM (такая же, как для DeepSeek) ---
class TaskLabel(BaseModel):
    """Структура, которую мы ожидаем от модели."""
    skill_id: str = Field(description="ID навыка из предоставленной таксономии")
    difficulty: float = Field(ge=0.0, le=1.0, description="Сложность от 0.0 до 1.0")
    confidence: float = Field(ge=0.0, le=1.0, description="Уверенность модели в разметке")
    reasoning: str = Field(description="Краткое обоснование выбора навыка и сложности")


# --- Загрузка таксономии для промпта (функция без изменений) ---
def load_taxonomy_text():
    tax_path = Path(__file__).parent.parent / "taxonomy" / "informatics_10_11.yaml"
    with open(tax_path, encoding="utf-8") as f:
        taxonomy = yaml.safe_load(f)
    lines = []
    for module in taxonomy:
        for topic in module.get("topics", []):
            for skill in topic.get("skills", []):
                lines.append(f'- ID: "{skill["id"]}", Название: "{skill["name"]}"')
    return "\n".join(lines)

# --- Промпт (такой же, как для DeepSeek) ---
# ВАЖНО: Текст промпта нужно будет адаптировать под GigaChat, если потребуется.
# Сейчас можно использовать тот же самый SYSTEM_PROMPT_TEMPLATE, что и для DeepSeek.
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
  "difficulty": 0.2,
  "confidence": 0.95,
  "reasoning": "1) Проверяется навык перевода единиц измерения информации (байты → биты). 2) Одно действие: 4 × 8 = 32. 3) Сложность 0.2 — ученик знает формулу и применяет её напрямую."
}}

── ЭТАЛОН 2: СРЕДНЕЕ (difficulty = 0.49) ──
Задание: "Переведите число 255 из десятичной системы счисления в шестнадцатеричную."
Ответ:
{{
  "skill_id": "s_dec_to_base",
  "difficulty": 0.5,
  "confidence": 0.9,
  "reasoning": "1) Проверяется навык перевода из 10-й в 16-ю СС. 2) Два шага: деление на 16, запись остатков в обратном порядке. 3) Сложность 0.5 — ученик знает метод, но должен аккуратно выполнить деление и не перепутать порядок."
}}

── ЭТАЛОН 3: СЛОЖНОЕ (difficulty = 0.77) ──
Задание: "По каналу связи передаются сообщения из четырёх букв: А, Б, В, Г. Используется двоичный код, удовлетворяющий условию Фано. Для А, Б, В используются кодовые слова 0, 10, 110. Укажите кратчайшее кодовое слово для Г."
Ответ:
{{
  "skill_id": "s_fano_direct",
  "difficulty": 0.75,
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
"""

def label_task(task_text: str) -> TaskLabel | None:
    """Отправляет задание в GigaChat и возвращает структурированный ответ."""
    try:
        # Формируем запрос с использованием JSON-схемы для структурированного ответа
        # GigaChat поддерживает генерацию JSON по схеме[reference:8]
        chat = Chat(
            model=MODEL,
            messages=[
                Messages(role=MessagesRole.SYSTEM, content=SYSTEM_PROMPT_TEMPLATE.format(taxonomy=load_taxonomy_text())),
                Messages(role=MessagesRole.USER, content=f"Разметь это задание: {task_text}")
            ],
            # Используем response_format для принудительной генерации JSON по нашей схеме
            response_format={
                "type": "json_schema",
                "schema": TaskLabel.model_json_schema()
            }
        )
        
        response = client.chat(chat)
        content = response.choices[0].message.content
        
        # Валидируем полученный JSON с помощью Pydantic
        label = TaskLabel.model_validate_json(content)
        return label
    except Exception as e:
        print(f"  Ошибка при разметке: {e}")
        return None

def main():
    """Основной цикл: находит неразмеченные задания, размечает их и сохраняет."""
    with engine.begin() as conn:
        # Находим задания, у которых еще нет разметки от GigaChat
        tasks_to_label = conn.execute(text("""
            SELECT t.id, t.code, t.text 
            FROM tasks t
            LEFT JOIN task_labels tl ON tl.task_id = t.id AND tl.model = 'gigachat'
            WHERE tl.task_id IS NULL
            ORDER BY t.code
        """)).fetchall()

        if not tasks_to_label:
            print("Все задания уже размечены.")
            return

        print(f"Найдено {len(tasks_to_label)} заданий для разметки.")

        for task_id, code, task_text in tasks_to_label:
            print(f"  Разметка {code}...")
            label = label_task(task_text)
            
            if label:
                # Сохраняем результат в PostgreSQL
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
                "tid": task_id,
                "sid": label.skill_id,
                "diff": label.difficulty,
                "conf": label.confidence,
                "reason": label.reasoning,
            })
                print(f"    -> Навык: {label.skill_id}, Сложность: {label.difficulty:.2f}")
            else:
                print(f"    -> Не удалось разметить.")

    print("\nРазметка завершена.")

if __name__ == "__main__":
    main()