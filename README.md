# HyperUm

Система гиперперсонализации образовательного процесса
на основе графов знаний и ML-моделей.

**ВКР бакалавра** · 09.03.02 «Информационные системы и технологии»
Профиль: Машинное обучение и искусственный интеллект
Тема: «Система гиперперсонализации образовательного процесса
на основе графов знаний и ML-моделей»

**Статус:** MVP работает. Апробация в лицее при ТПУ идёт.

---

## Что это

HyperUm — интеллектуальный ассистент учителя. Система:

- ведёт банк заданий с разметкой по навыкам и сложности (автоматически через LLM);
- принимает ответы учеников (Яндекс.Формы + PWA в разработке);
- автоматически проверяет ответы и считает mastery по каждому навыку;
- **генерирует персональные тесты** — каждому ученику свой набор заданий;
- показывает учителю дашборд: кто что знает, где проблемы;
- даёт ученику приложение с его графом знаний.

Ключевое отличие от аналогов (Учи.ру, ЯКласс): система **не заменяет**
учителя и **не раздаёт** всем одинаковые задания. Учитель задаёт тему,
жмёт кнопку — получает **N персональных тестов для N учеников**.

---

## Архитектура

```
              ┌─────────────────────┐
              │   taxonomy/*.yaml   │  ← источник истины
              └──────────┬──────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        ┌───────────┐         ┌──────────┐
        │ PostgreSQL│         │  Neo4j   │
        │           │         │          │
        │  tasks    │         │  Module  │
        │  users    │         │  Topic   │
        │  responses│         │  Skill   │
        │  mastery  │         │ PREREQ   │
        └─────┬─────┘         └────┬─────┘
              │                    │
              └──────────┬─────────┘
                         ▼
                ┌─────────────────┐
                │  FastAPI        │ ← единый API
                │  (backend/)     │
                └────────┬────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌───────────────┐ ┌──────────────┐ ┌─────────────┐
│  PWA ученика  │ │  Дашборд     │ │  Платформа  │
│  (в разраб.)  │ │  учителя     │ │  ПолиУм     │
│               │ │  (Streamlit) │ │  (внешний)  │
└───────────────┘ └──────────────┘ └─────────────┘
```

**Три уровня данных:**

| Уровень | Что | Sharing |
|---------|-----|---------|
| Global | Таксономия (`skills`) | Общий для всех |
| Shared | Задания, разметка, статистика | Общий, авторство сохраняется |
| Isolated | PII, ответы, mastery | Только внутри tenant'а (RLS) |

**Контексты применения:**
- **Школьный** (апробация идёт) — учитель + класс.
- **Платформенный** (в планах на февраль) — репетитор + ученики.

Ядро системы **не зависит** от контекста.

---

## Стек

| Слой | Технология |
|------|-----------|
| Backend | FastAPI + Python 3.11 |
| БД (транзакции) | PostgreSQL 16 + SQLAlchemy 2 |
| БД (граф) | Neo4j 5 |
| Разметка заданий | GigaChat / DeepSeek API |
| Аутентификация | JWT + bcrypt |
| Дашборд учителя | Streamlit |
| PWA ученика | React + Vite + TypeScript + Tailwind |
| Граф в UI | Cytoscape.js |
| Инфраструктура | Docker Compose |

---

## Требования

- Python 3.11+
- Node.js 20+ (для PWA)
- Docker Desktop
- Git

---

## Установка (один раз)

### 1. Клонировать и активировать venv

```powershell
cd hyperum
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Если PowerShell ругается на политику:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 2. Установить зависимости

```powershell
pip install -r requirements.txt
```

### 3. Настроить `.env`

Скопируй `.env.example` → `.env` и заполни:

```
HYPERUM_DB_URL=postgresql://hyperum:hyperum_dev@localhost:5432/hyperum
HYPERUM_NEO4J_URI=bolt://localhost:7687
HYPERUM_NEO4J_USER=neo4j
HYPERUM_NEO4J_PASSWORD=hyperum_dev
HYPERUM_TENANT_DEFAULT=school_lyceum
HYPERUM_JWT_SECRET=dev-secret-change-me-in-production
GIGACHAT_AUTH_KEY=ваш_ключ
DEEPSEEK_API_KEY=ваш_ключ
```

### 4. Поднять инфраструктуру

```powershell
docker compose up -d
docker compose ps
```

Оба контейнера — `running`: `hyperum_postgres`, `hyperum_neo4j`.

### 5. Применить миграции

```powershell
.\scripts\migrate.ps1
```

### 6. Загрузить таксономию

```powershell
python -m ml.load_taxonomy        # → Neo4j
python -m ml.sync_skills_to_pg    # → PostgreSQL
```

Проверка: ~140 навыков, 12 модулей.

### 7. Загрузить задания и разметить

```powershell
python -m scripts.seed_tasks
python -m scripts.import_tasks tasks/batch2.csv
```

Разметка через DeepSeek — автоматически.

### 8. Установить пароль учителю

```powershell
python -m scripts.set_password vee4@tpu.ru mypassword123
```

Готово. Можно работать.

---

## 🚀 Ежедневное использование

Система состоит из **трёх компонентов**, запускаемых отдельно:

### API (FastAPI)

```powershell
uvicorn backend.main:app --reload --port 8000
```

- **Swagger UI:** http://localhost:8000/docs
- **Health:** http://localhost:8000/health/db

Подробнее — `backend/README.md`.

### Дашборд учителя (Streamlit)

```powershell
streamlit run dashboard/app.py
```

- Откроется http://localhost:8501.
- **6 экранов:** Обзор, Тепловая карта, Проблемные темы, Ученики, Задания, Создать тест.

### PWA ученика

```powershell
cd pwa
npm run dev
```

- Откроется http://localhost:5173.
- В разработке (см. раздел «Roadmap»).

---

## 📋 Полный рабочий цикл

### Сценарий A. Через Яндекс.Формы (работает сейчас)

**1. Создать тест в Яндекс.Формах**

В заголовке каждого вопроса — код задания `[task_XXX]`:

```
[task_001] Сколько будет 1010₂ + 110₂?
```

Поля формы: **ФИО**, **Класс**.

**2. Скачать CSV**

Яндекс.Формы → **Ответы** → **Скачать CSV** → `data/check_YYYY-MM-DD.csv`.

**3. Импортировать**

```powershell
python -m ingest.parse_yandex_csv data/check_2026-10-05.csv
python -m ml.compute_mastery
```

**4. Посмотреть**

```powershell
streamlit run dashboard/app.py
```

### Сценарий B. Через API (генерация + отправка)

**1. Залогинься как учитель**

`POST /api/v1/auth/login` с email и паролем.

**2. Сгенерируй тест**

`POST /api/v1/assignments/generate`:

```json
{
  "class_name": "10А",
  "topic": "Кодирование",
  "n_tasks": 3
}
```

**3. Сохрани и отправь**

- `POST /api/v1/assignments/save` — сохранить черновик.
- `POST /api/v1/assignments/{id}/send` — отправить.

**4. Ученик решает**

- Логинится в PWA (в разработке).
- `GET /api/v1/assignments/my` — активные тесты.
- `POST /api/v1/responses` — отправить ответ.

---

## ➕ Добавление новых заданий

### Через CSV (рекомендуется)

Создай `tasks/my_batch.csv`:

```csv
code,text,answer,type
task_012,"Сколько байт в 2 Кбайтах?","2048",text
task_013,"Переведите 100 в двоичную.","1100100",text
```

Загрузи и разметь автоматически через GigaChat/DeepSeek:

```powershell
python -m scripts.import_tasks tasks/my_batch.csv
```

**Опции:**
- `--import-only` — только загрузить, без разметки
- `--relabel` — переразметить все задания заново

### Разметка вручную

Если точно знаешь навык — добавь колонки в CSV:

```csv
code,text,answer,type,skill_id,difficulty
task_015,"Сколько 7+5 в двоичной?","1100",text,s_arith_in_base,0.45
```

LLM **не тронет** эти задания.

### Переразметка через DeepSeek

```powershell
python -m ml.label_tasks_with_deepseek
```

### Нормализация сложностей

После разметки — выровнять распределение:

```powershell
python -m ml.normalize_difficulty
```

(LLM склонны кластеризовать сложности в узком диапазоне. Этот скрипт переводит их в равномерную шкалу.)

---

## 🎯 Генератор персональных тестов

### Через дашборд

Streamlit → **🎯 Создать тест**:

1. Выбери класс, тему, число заданий.
2. Нажми **✨ Сгенерировать**.
3. Превью: список учеников, каждому — **свой** набор.
4. **💾 Сохранить черновик** → запись в БД.

### Как работает

Три механизма персонализации:

1. **IRT-модель scoring** — задание в зоне ближайшего развития (P ≈ 0.7).
2. **Diversity** — задания распределяются по классу, не дублируются.
3. **Prerequisite-проверка** — через Neo4j исключаются задания с проваленными предпосылками.

**Пример результата** (класс 10А, тема «Кодирование», 5 заданий):

```
Архипова:  task_215, task_206, task_046, task_286, task_044
Богословский: task_139, task_150, task_308, task_293, task_043
Буркин:    task_084, task_121, task_302, task_336, task_044
```

У каждого — свой набор. У **слабых** (Гурина) — задачи 0.4–0.5, у **сильных** (Богословский) — 0.75–0.85.

---

## 🔍 SQL-аналитика

Все запросы в `sql/`. Запуск:

```powershell
.\scripts\run_sql.ps1 sql\01_class_overview.sql
```

Все сразу:

```powershell
.\scripts\run_all_sql.ps1
```

**Что есть:**
- `01_class_overview` — KPI по классам
- `02_problems_by_class` — проблемные темы
- `03_weak_students` — отстающие
- `04_pivot_by_class` — матрица класс × навык
- `05_errors_by_class` — ошибки по навыкам
- `06_student_detail` — детали по ученику
- `07_skill_detail` — детали по навыку
- `08_task_stats` — статистика по заданиям
- `09_mastery_distribution` — распределение mastery
- `10_student_weak_skills` — что завалил каждый

---

## 🗂 Структура проекта

```
hyperum/
├── backend/              # FastAPI
│   ├── api/              # роутеры
│   ├── services/         # бизнес-логика
│   ├── models/           # Pydantic-схемы
│   ├── auth/             # JWT, bcrypt
│   ├── db/               # подключения к БД
│   ├── main.py
│   └── README.md         # ← документация API
│
├── dashboard/            # Streamlit
│   ├── app.py            # главный файл
│   ├── db.py             # запросы
│   └── generator.py      # генератор тестов
│
├── pwa/                  # PWA ученика (в разработке)
│   ├── src/
│   ├── public/
│   └── package.json
│
├── data/                 # CSV из Яндекс.Форм
├── ingest/               # парсинг CSV
│   ├── normalize.py
│   └── parse_yandex_csv.py
│
├── migrations/           # SQL-миграции
├── ml/                   # ML и загрузка данных
│   ├── load_taxonomy.py
│   ├── sync_skills_to_pg.py
│   ├── compute_mastery.py
│   ├── label_tasks_with_deepseek.py
│   ├── label_tasks_with_gigachat.py
│   ├── normalize_difficulty.py
│   └── sync_mastery_to_neo4j.py
│
├── scripts/              # утилиты
│   ├── migrate.ps1/.sh
│   ├── run_sql.ps1
│   ├── run_all_sql.ps1
│   ├── seed_tasks.py
│   ├── import_tasks.py
│   ├── set_password.py
│   ├── create_student.py
│   └── ...
│
├── sql/                  # аналитические запросы
├── tasks/                # CSV с заданиями
│   └── _template.csv
├── taxonomy/             # YAML с таксономией
│   └── informatics_10_11.yaml
├── tests/                # тесты
├── docs/                 # документация
│   ├── requirements.md
│   └── architecture.md
│
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🛠 Полезные команды

### Docker

```powershell
docker compose up -d        # поднять
docker compose down         # остановить
docker compose down -v      # остановить + удалить данные
docker compose ps           # статус
docker compose logs -f      # логи
```

### PostgreSQL

```powershell
# Зайти в psql
docker exec -it hyperum_postgres psql -U hyperum -d hyperum

# Быстрый запрос
docker exec -it hyperum_postgres psql -U hyperum -d hyperum -c "SELECT COUNT(*) FROM users;"

# Дамп
docker exec hyperum_postgres pg_dump -U hyperum hyperum > backup.sql
```

### Neo4j

Браузер: http://localhost:7474 · `neo4j` / `hyperum_dev`

```cypher
// Весь граф
MATCH (n) RETURN n LIMIT 100

// Иерархия
MATCH (m:Module)-[:CONTAINS]->(t:Topic)-[:CONTAINS]->(s:Skill)
RETURN m.name, t.name, s.name

// Mastery ученика
MATCH (st:Student)-[m:MASTERY]->(s:Skill)
RETURN st.id, s.name, m.value
LIMIT 20
```

### Тесты

```powershell
python -m tests.test_normalize
```

---

## 🎓 Правила разработки

### Запуск Python-скриптов

Всегда **из корня проекта** через `-m`:

```powershell
python -m ml.compute_mastery         # ✅
python ml/compute_mastery.py         # ❌ упадёт на импортах
```

### Логика сравнения ответов

Только через `ingest.normalize.answers_equal`:

```python
from ingest.normalize import answers_equal
correct = answers_equal(student_answer, expected_answer, task_type)
```

Защищает от `21.0` vs `21`, `FF` vs `ff`, `" 21 "` vs `21` и т.д.

### SQL с кириллицей

**Не через `Get-Content | docker exec`** — ломается кодировка.

**Правильно:**

```powershell
.\scripts\run_sql.ps1 sql\01_class_overview.sql
```

### Кодировка файлов

Все `.py`, `.sql`, `.yaml`, `.csv` — **UTF-8 без BOM**.

---

## 🐛 Troubleshooting

| Проблема | Решение |
|----------|---------|
| `ModuleNotFoundError: backend` | Запускай из корня: `uvicorn backend.main:app` |
| `ModuleNotFoundError: X` | Активируй venv: `.\.venv\Scripts\Activate.ps1` |
| `Cannot connect to Neo4j` | Подожди 30 сек, проверь `docker compose ps` |
| `psql: database "hyperum" does not exist` | `docker compose down -v && docker compose up -d` |
| `permission denied for table responses` | RLS: нужен `SET app.current_tenant` |
| Кириллица в psql — квадратики | Используй `run_sql.ps1` или дашборд |
| Дашборд пустой | Проверь `docker compose ps` |
| `Import matplotlib failed` | `pip install matplotlib` |
| `bcrypt version` warning | Игнорируй — passlib удалён, используется чистый bcrypt |
| `401 Unauthorized` в API | `POST /auth/login` сначала |

---

## 📝 Ключевые файлы для понимания

| Файл | Что внутри |
|------|-----------|
| `docs/requirements.md` | Что система должна делать (со статусами) |
| `docs/architecture.md` | Как она устроена |
| `backend/README.md` | Документация API |
| `taxonomy/informatics_10_11.yaml` | Источник истины по навыкам |
| `dashboard/generator.py` | Ядро гиперперсонализации |
| `ingest/normalize.py` | Логика сравнения ответов |
| `backend/services/responses_service.py` | Мгновенная проверка + обновление mastery |

---

## 📌 Итог одной командой

### Полный цикл для новой проверочной

```powershell
# 1. Поднять инфраструктуру
docker compose up -d

# 2. Импорт ответов из CSV
python -m ingest.parse_yandex_csv data/check_2026-10-05.csv
python -m ml.compute_mastery

# 3. Дашборд учителя
streamlit run dashboard/app.py

# 4. (опционально) API для PWA / интеграций
uvicorn backend.main:app --reload --port 8000
```

---

## Roadmap

| Период | Что | Статус |
|--------|-----|--------|
| Сентябрь 2026 | Ядро + дашборд + пилот + генератор | ✅ |
| Октябрь 2026 | FastAPI + расширение банка + PWA (старт) | 🟡 |
| Ноябрь 2026 | PWA (завершение) + деплой на VPS | 🔴 |
| Декабрь 2026 | ML-модуль (BKT, рекомендации) | 🔴 |
| Январь 2027 | Интеграция с ПолиУмом | 🔴 |
| Февраль–Март 2027 | Апробация на платформе | 🔴 |
| Апрель 2027 | ВКР | 🔴 |
| Май 2027 | Защита | 🔴 |

---

## Контакты

**Автор:** Епифанов Вячеслав Евгеньевич
**Научный руководитель:** Кривошеев Николай Анатольевич
**Организация:** Томский политехнический университет, 2026
**Апробация:** Лицей при ТПУ (3 класса, 67 учеников)