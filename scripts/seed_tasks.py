"""
Загрузка всех заданий в систему.
Идемпотентно: можно запускать многократно.
"""
import os
import uuid
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.getenv("HYPERUM_DB_URL"))

TASKS = [
    # ─── Базовые (task_001 … task_005) ───
    {
        "code": "task_001",
        "text": "Сколько будет 1010₂ + 110₂? Ответ в десятичной.",
        "answer": "16",
        "skill": "s_base_to_dec",
        "difficulty": 0.4,
    },
    {
        "code": "task_002",
        "text": "Переведите число 255 из десятичной в шестнадцатеричную.",
        "answer": "FF",
        "skill": "s_dec_to_base",
        "difficulty": 0.5,
    },
    {
        "code": "task_003",
        "text": "Сколько будет 12₈ + 7₈? Ответ в восьмеричной.",
        "answer": "21",
        "skill": "s_arith_in_base",
        "difficulty": 0.65,
    },
    {
        "code": "task_004",
        "text": "Что выведет код: for i in range(3): print(i)",
        "answer": "0 1 2",
        "skill": "s_for",
        "difficulty": 0.3,
    },
    {
        "code": "task_005",
        "text": "Сколько раз выполнится тело цикла: for i in range(1, 10, 2)?",
        "answer": "5",
        "skill": "s_for",
        "difficulty": 0.45,
    },

    # ─── Теория информации (task_006 … task_011) ───
    {
        "code": "task_006",
        "text": "Сколько бит информации содержит сообщение из 32 символов, если мощность используемого алфавита равна 64 символам?",
        "answer": "192",
        "skill": "s_volume",
        "difficulty": 0.3,
    },
    {
        "code": "task_007",
        "text": "По каналу связи передаются сообщения, содержащие только четыре буквы: А, Б, В, Г. Для передачи используется двоичный код, удовлетворяющий условию Фано. Для букв А, Б, В используются кодовые слова 0, 10, 110 соответственно. Укажите кратчайшее кодовое слово для буквы Г.",
        "answer": "111",
        "skill": "s_fano_direct",
        "difficulty": 0.5,
    },
    {
        "code": "task_008",
        "text": "При регистрации в компьютерной системе каждому пользователю выдаётся пароль, состоящий из 10 символов и содержащий только символы из 12-символьного набора. В базе данных для хранения каждого пароля отведено одинаковое и минимально возможное целое число байт. Определите объём памяти в байтах для хранения 50 паролей.",
        "answer": "250",
        "skill": "s_password",
        "difficulty": 0.6,
    },
    {
        "code": "task_009",
        "text": "Какой минимальный объём памяти в Кбайт нужно зарезервировать, чтобы можно было сохранить любое растровое изображение размером 128×320 пикселей при условии, что в изображении могут использоваться 64 различных цвета? В ответе запишите только целое число, единицу измерения писать не нужно.",
        "answer": "30",
        "skill": "s_image",
        "difficulty": 0.55,
    },
    {
        "code": "task_010",
        "text": "Скорость передачи данных через ADSL-соединение равна 512000 бит/с. Через данное соединение передают файл размером 1000 Кбайт. Определите время передачи файла в секундах.",
        "answer": "16",
        "skill": "s_transfer_speed",
        "difficulty": 0.5,
    },
    {
        "code": "task_011",
        "text": "Производится одноканальная (моно) звукозапись с частотой дискретизации 16 кГц и 16-битным разрешением. Запись длится 1 минуту. Определите размер файла в Кбайт.",
        "answer": "1875",
        "skill": "s_sound_image",
        "difficulty": 0.6,
    },
]


def upsert_task(conn, t):
    task_id = str(uuid.uuid4())
    existing = conn.execute(
        text("SELECT id FROM tasks WHERE code = :c"),
        {"c": t["code"]}
    ).fetchone()

    if existing:
        task_id = existing[0]
        conn.execute(text("""
            UPDATE tasks
            SET text = :text, answer = :answer, type = 'text'
            WHERE id = :id
        """), {"text": t["text"], "answer": t["answer"], "id": task_id})
        action = "updated"
    else:
        conn.execute(text("""
            INSERT INTO tasks (id, code, text, answer, type, visibility)
            VALUES (:id, :code, :text, :answer, 'text', 'shared')
        """), {
            "id": task_id, "code": t["code"],
            "text": t["text"], "answer": t["answer"]
        })
        action = "created"

    conn.execute(text("""
        INSERT INTO task_labels (task_id, skill_id, difficulty, confidence, model)
        VALUES (:tid, :sid, :d, 1.0, 'manual')
        ON CONFLICT (task_id, skill_id) DO UPDATE
          SET difficulty = EXCLUDED.difficulty,
              confidence = EXCLUDED.confidence,
              model = EXCLUDED.model
    """), {"tid": task_id, "sid": t["skill"], "d": t["difficulty"]})

    return action


def main():
    with engine.begin() as conn:
        for t in TASKS:
            action = upsert_task(conn, t)
            print(f"  [{action:>7}] {t['code']} -> {t['skill']}")
    print(f"\nВсего заданий: {len(TASKS)}")


if __name__ == "__main__":
    main()