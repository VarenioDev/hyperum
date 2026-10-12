# 🧠 HyperUm

**Система гиперперсонализации образовательного процесса
на основе графов знаний и ML-моделей.**

> Одна кнопка — N персональных тестов для N учеников.

[![ВКР](https://img.shields.io/badge/ВКР-09.03.02-blue)]()
[![Статус](https://img.shields.io/badge/статус-пилот%20идёт-green)]()
[![Деплой](https://img.shields.io/badge/prod-hyperum.polyum.ru-success)](https://hyperum.polyum.ru)
[![Python](https://img.shields.io/badge/python-3.11+-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.1-009688)]()
[![React](https://img.shields.io/badge/React-18-61dafb)]()

**Развёрнуто:** https://hyperum.polyum.ru  
**Апробация:** Лицей при ТПУ · 3 класса · 67 учеников  
**ВКР:** бакалаврская работа, ТПУ, 2026–2027

---

## Что это

HyperUm — **интеллектуальный ассистент учителя**. Система:

- ведёт банк заданий с multi-skill разметкой через LLM (DeepSeek);
- принимает ответы учеников через PWA и Яндекс.Формы;
- автоматически проверяет ответы, считает mastery по каждому навыку;
- **генерирует персональные тесты** — каждому ученику свой набор;
- показывает учителю, кто что знает и где проблемы;
- даёт ученику граф знаний с раскраской по освоению.

**Ключевое отличие** от Учи.ру, ЯКласс и подобных: система **не заменяет**
учителя и **не раздаёт** всем одинаковые задания. Учитель задаёт тему, жмёт
кнопку — получает **N персональных тестов для N учеников** с опорой
на граф знаний каждого.

---

## Научная цель (для ВКР)

HyperUm — это **не просто продукт**. Это **фабрика данных** для обучения
модели, которая должна **заменить эвристический подбор заданий**
на обученный на реальных данных.

**Текущее состояние (baseline):**

- Mastery считается формулой: взвешенный `correct / attempts` + сглаживание.
- Подбор заданий — IRT-подобная функция полезности (эвристика).
- Prerequisite-фильтр — порог mastery < 0.5.

**Что делаем дальше:**

1. **Фаза 1 (декабрь 2026).** Обучаем **BKT** (Bayesian Knowledge Tracing)
   на данных пилота. Проверяем гипотезу **H2:** BKT точнее эвристики
   в предсказании правильного ответа.
2. **Фаза 2 (январь 2027).** Делаем BKT **граф-осознанным**:
   учитываем prerequisite-связи между навыками. Проверяем гипотезу **H3:**
   graph-BKT точнее на редких навыках (где у ученика мало ответов).
3. **Фаза 3 (февраль–март 2027).** Внедряем в прод + **A/B тест**
   гиперперсонализации. Проверяем **H4:** обученная модель даёт прирост
   освоения материала.

**Почему это научно:** граф-aware Knowledge Tracing — активная область
исследований (GKT, DGEKT, HiTKT). Мы применяем её к **реальной школьной
системе** с 67 живыми учениками, что даёт прикладной вклад.

Полная научная рамка — в [`docs/research.md`](docs/research.md).

---

## Ключевые фичи

| Фича | Что делает | Статус |
|------|-----------|--------|
| 🎯 **Генерация персональных тестов** | Одно нажатие → N уникальных наборов | ✅ |
| 🌳 **Граф знаний** | Prerequisite-связи, визуализация (Cytoscape) | ✅ |
| 🤖 **LLM-разметка** | DeepSeek автоматически размечает задания | ✅ |
| 📊 **Mastery по навыкам** | Взвешенный, сглаженный, обновляется онлайн | ✅ |
| 📱 **PWA для ученика** | Устанавливается на домашний экран | ✅ |
| 👩‍🏫 **Кабинет учителя** | Классы, генерация, approve учеников | ✅ |
| 🔗 **Инвайт-коды** | Ученики регистрируются сами | ✅ |
| 🎨 **Demo-режим** | Гость получает тест без регистрации | ✅ |
| 🧠 **BKT / graph-BKT** | Заменяет эвристический mastery | 🔴 (в планах) |

---

## Скриншоты

> _Скриншоты будут добавлены в финальной версии ВКР._
> Публичный demo: https://hyperum.polyum.ru

```
┌─────────────────────────┐  ┌─────────────────────────┐
│   🧠 HyperUm            │  │   Привет, Ваня!         │
│                         │  │                         │
│  Персональные задания — │  │  [средний] [освоено]    │
│     каждому ученику     │  │   [подтянуть]           │
│                         │  │                         │
│  ┌─────────────────┐    │  │  Активные задания       │
│  │ Опиши свой      │    │  │  ┌─────────────────┐    │
│  │ уровень...      │    │  │  │ 🎯 Кодирование  │    │
│  │                 │    │  │  │ 2 из 5          │    │
│  └─────────────────┘    │  │  └─────────────────┘    │
│                         │  │                         │
│  ✨ Получить тест       │  │  Стоит подтянуть        │
│                         │  │  Цикл for        0.42   │
└─────────────────────────┘  └─────────────────────────┘
   Лендинг с demo               Дашборд ученика

┌─────────────────────────┐  ┌─────────────────────────┐
│ 10А · 22 учеников       │  │ Твой граф знаний        │
│                         │  │                         │
│ ✨ Сгенерировать        │  │   ●───●───●───●          │
│    персональные тесты   │  │   │   │   │   │          │
│                         │  │   ●───●───●───●          │
│ Код класса: A7K9P2      │  │   │   │   │   │          │
│                         │  │   ●───●───●───●          │
│ Ждут подтверждения (2)  │  │                         │
│ Ученики (20)            │  │ 🟢 Освоено  🟡 В процессе│
│ 🎯 Иванов · 2 теста     │  │ 🔴 Слабо    ⚪ Не изучено │
└─────────────────────────┘  └─────────────────────────┘
   Класс учителя                Граф знаний
```

---

## Стек

| Слой | Технология |
|------|-----------|
| **Backend** | FastAPI + Python 3.11 |
| **БД (транзакции)** | PostgreSQL 16 + SQLAlchemy 2 + RLS |
| **БД (граф)** | Neo4j 5 |
| **LLM** | DeepSeek (`deepseek-chat`) |
| **Аутентификация** | JWT (cookies + Bearer) + bcrypt |
| **PWA (ученик + учитель)** | React 18 + Vite + TypeScript + Tailwind |
| **State / Data** | Zustand + TanStack Query |
| **Граф в UI** | Cytoscape.js + dagre |
| **PWA-манифест** | vite-plugin-pwa + Workbox |
| **Инфра** | Docker Compose + Nginx + Let's Encrypt |
| **Деплой** | VPS, `hyperum.polyum.ru` |

---

## Архитектура (краткая схема)

```
       ┌─────────────────────────────────────────────┐
       │              КЛИЕНТЫ (PWA)                  │
       │  Ученик  ·  Учитель  ·  Гость (лендинг)     │
       └──────────────────┬──────────────────────────┘
                          │ REST + JWT
                          ▼
       ┌─────────────────────────────────────────────┐
       │           NGINX (hyperum.polyum.ru)         │
       └──────────────────┬──────────────────────────┘
                          ▼
       ┌─────────────────────────────────────────────┐
       │              BACKEND (FastAPI)              │
       │  auth · tasks · mastery · graph · groups ·  │
       │  assignments · responses · demo             │
       └──┬───────────────────┬──────────────────────┘
          │                   │
          ▼                   ▼
    ┌──────────┐       ┌──────────┐       ┌──────────┐
    │PostgreSQL│       │  Neo4j   │       │ DeepSeek │
    │          │       │          │       │          │
    │ users    │       │ Module   │       │ разметка │
    │ tasks    │       │ Topic    │       │ demo     │
    │ responses│       │ Skill    │       │          │
    │ mastery  │       │ PREREQ   │       │          │
    │ assigns  │       │ Student  │       │          │
    └──────────┘       └──────────┘       └──────────┘
```

**Полная архитектура** — в [`docs/architecture.md`](docs/architecture.md).

---

## Быстрый старт (dev)

### Требования

- Python 3.11+
- Node.js 20+
- Docker Desktop
- Git

### Установка

```powershell
# 1. Клонирование
git clone <repo-url> hyperum
cd hyperum

# 2. venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# если политика запрещает:
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 3. Зависимости
pip install -r requirements-backend.txt

# 4. .env
Copy-Item .env.example .env
# заполнить: HYPERUM_DB_URL, NEO4J_*, JWT_SECRET, DEEPSEEK_API_KEY

# 5. Инфраструктура
docker compose up -d
docker compose ps

# 6. Миграции
.\scripts\migrate.ps1

# 7. Таксономия
python -m ml.load_taxonomy
python -m ml.sync_skills_to_pg

# 8. Задания
python -m scripts.seed_tasks

# 9. Разметка через DeepSeek
python -m ml.label_tasks_with_deepseek

# 10. Учитель
python -m scripts.set_password vee4@tpu.ru mypassword
```

### Ежедневный запуск

**Терминал 1 — Backend:**
```powershell
.\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload --port 8000
```

**Терминал 2 — PWA:**
```powershell
cd pwa
npm run dev
```

**Терминал 3 — БД:**
```powershell
docker compose up -d
```

**Открыть:**

- 🌐 PWA: http://localhost:5173
- 📖 API Swagger: http://localhost:8000/docs
- 🩺 Health: http://localhost:8000/health/db
- 🕸 Neo4j Browser: http://localhost:7474

---

## Деплой

Прод — на VPS, домен **hyperum.polyum.ru**, HTTPS через Let's Encrypt,
reverse proxy на Nginx, backend в Docker.

Полная инструкция — в [`docs/deployment.md`](docs/deployment.md).

**Кратко:**

```bash
# На VPS
cd /root/hyperum
./scripts/deploy.sh
```

---

## Структура проекта

```
hyperum/
├── backend/              # FastAPI: роутеры, сервисы, модели
│   ├── api/              # HTTP-роутеры
│   ├── services/         # бизнес-логика
│   ├── models/           # Pydantic-схемы
│   ├── auth/             # JWT + bcrypt
│   ├── db/               # PostgreSQL + Neo4j
│   ├── main.py
│   ├── config.py
│   └── Dockerfile
│
├── pwa/                  # React PWA (ученик + учитель)
│   ├── src/
│   │   ├── api/          # axios-клиент
│   │   ├── pages/        # Landing, Login, Dashboard, ...
│   │   ├── pages/teacher/
│   │   ├── components/   # GraphView, Header, ...
│   │   ├── stores/       # Zustand
│   │   └── hooks/
│   ├── public/
│   └── vite.config.ts
│
├── ml/                   # ML-скрипты
│   ├── load_taxonomy.py
│   ├── sync_skills_to_pg.py
│   ├── compute_mastery.py
│   ├── label_tasks_with_deepseek.py
│   ├── normalize_difficulty.py
│   └── prompts/
│
├── ingest/               # Парсинг CSV Яндекс.Форм
│   ├── normalize.py      # answers_equal
│   └── parse_yandex_csv.py
│
├── migrations/           # 18 SQL-миграций
├── scripts/              # Утилиты (deploy, migrate, seed)
├── sql/                  # Аналитические запросы
├── taxonomy/             # YAML с таксономией
├── tasks/                # CSV с заданиями
├── dashboard/            # Streamlit (устарел, legacy)
├── docs/                 # Документация
├── tests/
├── docker-compose.yml
├── docker-compose.prod.yml
├── requirements.txt
├── requirements-backend.txt
└── README.md
```

---

## Документация

Вся актуальная документация — в папке [`docs/`](docs/).

| Документ | О чём |
|----------|-------|
| [`glossary.md`](docs/glossary.md) | Словарь терминов проекта |
| [`architecture.md`](docs/architecture.md) | Архитектура: компоненты, потоки данных |
| [`data-model.md`](docs/data-model.md) | Схема PostgreSQL + Neo4j |
| [`ml.md`](docs/ml.md) | Mastery, scoring, разметка, roadmap ML |
| [`research.md`](docs/research.md) | **Научная рамка ВКР:** гипотезы H1–H5, метрики, план эксперимента |
| [`requirements.md`](docs/requirements.md) | Требования и актуальные статусы |
| [`api.md`](docs/api.md) | Обзор REST API |
| [`user-flows.md`](docs/user-flows.md) | Сценарии по ролям |
| [`deployment.md`](docs/deployment.md) | Развёртывание: dev + prod VPS |
| [`decisions.md`](docs/decisions.md) | 16 ADR: почему так, а не иначе |

**Backend API:** [`backend/README.md`](backend/README.md) + `/docs` (Swagger).

---

## Статус и roadmap

### Текущее состояние (октябрь 2026)

- ✅ Пилот в лицее при ТПУ идёт (3 класса, 67 учеников)
- ✅ PWA ученика и учителя в проде
- ✅ Demo-режим на лендинге
- ✅ Multi-skill разметка через DeepSeek
- ✅ Генерация персональных тестов
- ✅ Граф знаний (ученик + класс)
- ✅ Регистрация по инвайт-коду

### До финала MVP (≈1 рабочий день)

| # | Что | Оценка |
|---|-----|--------|
| F45 | Дашборд ученика: прогресс + «Следующий шаг» + streak | 3–4 ч |
| F46 | `GET /mastery/me/summary` | 1 ч |
| F47 | `GET /recommendations/next` | 1–2 ч |
| F58–F60 | Плюрализация, «0/1» → «Сдался», дубликат | 45 мин |
| **F56** | **Бэкапы БД** ⚠️ критично | 1 ч |

### Roadmap ML (см. `docs/research.md`)

| Период | Что | Гипотеза |
|--------|-----|----------|
| Декабрь 2026 | BKT | **H2:** BKT > эвристики |
| Январь 2027 | Graph-BKT | **H3:** граф улучшает редкие навыки |
| Февраль–март 2027 | A/B тест | **H4:** гиперперсонализация даёт прирост |
| Апрель 2027 | Переносимость на ПолиУМ | **H5** |
| Апрель 2027 | ВКР | — |
| Май 2027 | Защита | — |

---

## Правила разработки

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

Защищает от `21.0` vs `21`, `FF` vs `ff`, лишних пробелов.

### SQL с кириллицей

**Не через `Get-Content | docker exec`** — ломается кодировка.

**Правильно:**

```powershell
.\scripts\run_sql.ps1 sql\01_class_overview.sql
```

### Кодировка файлов

Все `.py`, `.sql`, `.yaml`, `.csv` — **UTF-8 без BOM**.

---

## Troubleshooting

| Проблема | Решение |
|----------|---------|
| `ModuleNotFoundError: backend` | Запускай из корня: `uvicorn backend.main:app` |
| `ModuleNotFoundError: X` | Активируй venv: `.\.venv\Scripts\Activate.ps1` |
| `Cannot connect to Neo4j` | Подожди 30 сек, `docker compose ps` |
| `psql: database "hyperum" does not exist` | `docker compose down -v && docker compose up -d` |
| `permission denied for table responses` | RLS: нужен `tenant_session()` |
| Кириллица в psql — квадратики | Используй `run_sql.ps1` |
| `401 Unauthorized` в API | `POST /auth/login` сначала |
| 502 Bad Gateway на VPS | `docker compose logs backend` |

---

## Контакты

**Автор:** Епифанов Вячеслав Евгеньевич  
**Научный руководитель:** Кривошеев Николай Анатольевич  
**Организация:** Томский политехнический университет, 2026  
**Апробация:** Лицей при ТПУ · 3 класса · 67 учеников  
**Прод:** https://hyperum.polyum.ru

---

## Лицензия

Учебный проект. Используется в ВКР. Все права на таксономию,
задания и данные пилота — у автора и Лицея при ТПУ.