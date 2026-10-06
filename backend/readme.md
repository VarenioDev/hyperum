# HyperUm API

Backend-сервис системы гиперперсонализации HyperUm.
FastAPI + PostgreSQL + Neo4j.

**Версия:** 0.1.0
**Статус:** работает, покрывает все ключевые сценарии

---

## Что это

REST API, обслуживающий:
- PWA ученика (в разработке)
- дашборд учителя (Streamlit)
- интеграции с внешними платформами (ПолиУм)

Все эндпоинты под префиксом `/api/v1`. Документация — автоматическая, в `/docs`.

---

## Стек

| Компонент | Технология |
|-----------|-----------|
| Фреймворк | FastAPI |
| ASGI-сервер | Uvicorn |
| ORM | SQLAlchemy 2.0 |
| БД (транзакции) | PostgreSQL 16 |
| БД (граф) | Neo4j 5 |
| Аутентификация | JWT (httpOnly cookies + Bearer) |
| Хеширование паролей | bcrypt |
| Валидация | Pydantic 2 |

---

## Запуск

### Предварительно

Docker Compose с PostgreSQL и Neo4j **должен быть запущен**:

```powershell
# из корня проекта
docker compose up -d
docker compose ps
```

Оба контейнера — `running`: `hyperum_postgres`, `hyperum_neo4j`.

### Запуск API

Из корня проекта:

```powershell
uvicorn backend.main:app --reload --port 8000
```

**Флаги:**
- `--reload` — автоперезагрузка при изменении кода (для разработки)
- `--port 8000` — порт
- `--host 0.0.0.0` — если нужно, чтобы API был доступен из локальной сети

**Ожидаемый вывод:**

```
🚀 Starting HyperUm API v0.1.0
✅ PostgreSQL: connected
✅ Neo4j: connected
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### Проверка

- **Health:** http://localhost:8000/health
- **DB health:** http://localhost:8000/health/db
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Структура проекта

```
backend/
├── main.py               # точка входа, роутинг, lifespan
├── config.py             # настройки из .env
│
├── auth/                 # аутентификация
│   ├── security.py       # bcrypt, JWT
│   └── dependencies.py   # get_current_user, require_teacher
│
├── api/                  # HTTP-роутеры (тонкие)
│   ├── auth.py
│   ├── tasks.py
│   ├── mastery.py
│   ├── graph.py
│   ├── assignments.py
│   └── responses.py
│
├── services/             # бизнес-логика
│   ├── tasks_service.py
│   ├── mastery_service.py
│   ├── graph_service.py
│   ├── assignments_service.py
│   └── responses_service.py
│
├── models/               # Pydantic-схемы
│   ├── common.py
│   ├── auth.py
│   ├── users.py
│   ├── tasks.py
│   ├── assignments.py
│   ├── responses.py
│   └── graph.py
│
└── db/                   # подключения к БД
    ├── postgres.py       # engine, session, tenant_session
    └── neo4j.py          # driver, session
```

**Принцип:** роутер — тонкий (валидация + вызов сервиса), сервис — вся логика.

---

## Аутентификация

### Как работает

1. Ученик/учитель отправляет `POST /api/v1/auth/login` с email и паролем.
2. Сервер проверяет пароль (bcrypt), создаёт **access** (1 час) и **refresh** (30 дней) JWT.
3. Оба токена устанавливаются в **httpOnly cookies**:
   - `hyperum_access` — на все запросы
   - `hyperum_refresh` — только на `/auth/refresh` (пока заглушка)
4. Клиент (PWA) автоматически отправляет cookie с каждым запросом.
5. Сервер читает cookie, извлекает `tenant_id` и `role`, ставит RLS-контекст.

### Два способа передачи токена

**1. Cookie (для PWA)**

Ничего делать не нужно — браузер отправляет автоматически.

**2. Bearer-токен (для интеграций)**

```
Authorization: Bearer eyJhbGci...
```

Возвращается в JSON при `/auth/login`. Используется ПолиУмом и другими API-клиентами.

### Установка пароля

Пароли устанавливаются скриптом (не через API):

```powershell
# из корня проекта
python -m scripts.set_password vee4@tpu.ru mypassword123
```

Для создания нового ученика с паролем:

```powershell
python -m scripts.create_student "Иванов Иван Иванович" ivanov@lyceum.ru test1234
```

---

## Эндпоинты

Все эндпоинты — под префиксом `/api/v1`.

### `auth` — аутентификация

| Метод | Путь | Кому | Что |
|-------|------|------|-----|
| POST | `/auth/login` | Все | Вход по email + пароль |
| POST | `/auth/logout` | Все | Очистка cookies |
| GET | `/auth/me` | Все | Профиль + список учеников (для учителя) |

### `tasks` — справочник заданий

| Метод | Путь | Кому | Что |
|-------|------|------|-----|
| GET | `/tasks` | Авторизованные | Список с фильтрами и пагинацией |
| GET | `/tasks/{id}` | Авторизованные | Полное задание со всеми разметками |
| GET | `/tasks/{id}/labels` | Учитель | Только разметки задания |

**Фильтры `/tasks`:**
- `skill_id` — по навыку (`s_fano_direct`)
- `model` — модель разметки (`deepseek`, `gigachat`, `manual`)
- `limit`, `offset` — пагинация

### `mastery` — аналитика освоения

| Метод | Путь | Кому | Что |
|-------|------|------|-----|
| GET | `/mastery/me` | Ученик | Свой mastery |
| GET | `/mastery/student/{id}` | Учитель | Mastery ученика |
| GET | `/mastery/student/{id}/weak` | Учитель | Только слабые навыки |
| GET | `/mastery/class/{id}` | Учитель | Агрегат класса |
| GET | `/mastery/skills` | Учитель | Сводка по всем навыкам |

**Параметры:**
- `threshold` (для `/weak`) — порог слабого навыка (по умолчанию 0.5)

### `graph` — граф знаний

| Метод | Путь | Кому | Что |
|-------|------|------|-----|
| GET | `/graph/full` | Авторизованные | Полный предметный граф |
| GET | `/graph/student/{id}` | Учитель / сам ученик | Граф ученика с mastery |
| GET | `/graph/class/{id}` | Учитель | Агрегат класса |
| GET | `/graph/skill/{id}` | Авторизованные | Подграф вокруг навыка |

**Формат ответа:** узлы (`nodes`) и рёбра (`edges`) для Cytoscape.js.

**Статусы узла:** `mastered` (≥0.8), `learning` (0.5–0.8), `weak` (<0.5), `unknown`.

### `assignments` — генерация и отправка тестов

| Метод | Путь | Кому | Что |
|-------|------|------|-----|
| POST | `/assignments/generate` | Учитель | Сгенерировать preview (без сохранения) |
| POST | `/assignments/save` | Учитель | Сохранить черновик |
| POST | `/assignments/{id}/send` | Учитель | Отправить ученикам |
| GET | `/assignments` | Учитель | Список своих назначений |
| GET | `/assignments/my` | Ученик | Свои активные тесты |
| GET | `/assignments/{id}/tasks` | Ученик | Задания теста (без ответов) |

### `responses` — ответы учеников

| Метод | Путь | Кому | Что |
|-------|------|------|-----|
| POST | `/responses` | Ученик | Отправить ответ, мгновенная проверка |
| GET | `/responses/my` | Ученик | История ответов |
| GET | `/responses/task/{id}` | Учитель | Статистика по заданию |
| GET | `/responses/assignment/{id}` | Учитель | Прогресс по назначению |

---

## Полный рабочий поток

### Учитель генерирует и отправляет тест

```
1. POST /api/v1/auth/login
   { email, password }

2. POST /api/v1/assignments/generate
   { class_name: "10А", topic: "Кодирование", n_tasks: 3 }
   → получаем персональные тесты для каждого ученика

3. POST /api/v1/assignments/save
   { title, class_name, topic, students: [...] }
   → assignment_id, status: draft

4. POST /api/v1/assignments/{id}/send
   → status: sent, students_count: 25
```

### Ученик решает задания

```
1. POST /api/v1/auth/login
   { email, password }

2. GET /api/v1/assignments/my
   → список активных тестов

3. GET /api/v1/assignments/{id}/tasks
   → задания без правильных ответов

4. POST /api/v1/responses
   { task_id, answer, time_sec: 30 }
   → { correct, expected, new_mastery }

5. GET /api/v1/graph/student/{me}
   → обновлённый граф с новым mastery
```

---

## Примеры запросов (curl)

### Логин

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"email":"vee4@tpu.ru","password":"mypassword123"}'
```

Флаг `-c cookies.txt` сохраняет cookies. Дальше используем `-b cookies.txt`.

### Профиль

```bash
curl http://localhost:8000/api/v1/auth/me \
  -b cookies.txt
```

### Список заданий

```bash
curl "http://localhost:8000/api/v1/tasks?skill_id=s_fano_direct&limit=10" \
  -b cookies.txt
```

### Генерация теста

```bash
curl -X POST http://localhost:8000/api/v1/assignments/generate \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"class_name":"10А","topic":"Кодирование","n_tasks":3}'
```

### Отправка ответа

```bash
curl -X POST http://localhost:8000/api/v1/responses \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"task_id":"<UUID>","answer":"111","time_sec":42}'
```

---

## Архитектурные решения

### Multi-tenancy через RLS

Все isolated-таблицы (`responses`, `student_mastery`) защищены Row-Level Security. Backend в начале каждой сессии выполняет:

```sql
SET LOCAL app.current_tenant = '<tenant_id>';
```

`SET LOCAL` работает в пределах транзакции — при возврате соединения в пул переменная сбрасывается. Это **критично**: без `LOCAL` значение могло бы «протечь» в следующий запрос.

### Разделение данных

| Уровень | Что | tenant_id |
|---------|-----|-----------|
| Global | Таксономия (`skills`) | `'global'` |
| Shared | Задания, разметки | Без tenant_id |
| Isolated | Пользователи, ответы, mastery | Обязателен + RLS |

### Сглаженный mastery (Байесовское обновление)

После каждого ответа mastery пересчитывается:

```
mastery = (correct + 0.5 × 3) / (attempts + 3)
```

При малом числе попыток значение тянется к 0.5 (не доверяем единичным данным). При большом — доверяем статистике.

### Мгновенный sync в Neo4j

После отправки ответа mastery обновляется в:
1. PostgreSQL (`student_mastery`) — источник истины.
2. Neo4j (ребро `MASTERY`) — для визуализации графа.

Если Neo4j недоступен — ответ ученику всё равно возвращается. Sync — **не критичная операция**.

---

## Аутентификация: детали

### Структура JWT

```json
{
  "sub": "UUID пользователя",
  "tenant_id": "school_lyceum",
  "role": "owner | student | admin",
  "type": "access | refresh",
  "iat": 1234567890,
  "exp": 1234571490
}
```

### Проверка в зависимостях

```python
user = Depends(get_current_user)       # любой авторизованный
user = Depends(require_teacher)        # owner или admin
user = Depends(require_student)        # только student
```

### Cookies в проде

В `.env` и `backend/api/auth.py` есть флаг `secure`. Сейчас `False` — для разработки по HTTP.

**В продакшне обязательно `secure=True`.** Иначе токены будут передаваться по HTTP — уязвимость.

---

## Частые проблемы

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `ModuleNotFoundError: backend` | Запуск не из корня | `cd hyperum`, потом `uvicorn backend.main:app` |
| `❌ PostgreSQL: NOT available` | Docker не запущен | `docker compose up -d` |
| `❌ Neo4j: NOT available` | Neo4j стартует 30 сек | Подожди, проверь `docker compose ps` |
| `401 Unauthorized` | Не залогинен | `POST /auth/login` сначала |
| `403 Forbidden` | Не та роль | Проверь, под кем залогинен |
| `422 Unprocessable Entity` | Невалидное тело | Проверь JSON в `/docs` |
| `permission denied for table responses` | RLS не установлен | `tenant_session()` устанавливает автоматически |
| `CORS error` в браузере | Origin не в списке | Добавь в `allow_origins` в `main.py` |

---

## Что не реализовано (в планах)

| Функция | Приоритет |
|---------|-----------|
| `POST /auth/refresh` (обновление access по refresh) | SHOULD |
| Регистрация пользователей через API | SHOULD |
| Загрузка CSV через API (`POST /ingest/csv`) | SHOULD |
| WebSocket для real-time обновлений | COULD |
| Rate limiting | COULD |
| Полнотекстовый поиск по заданиям | COULD |

---

## Разработка

### Добавление нового эндпоинта

1. Создай/обнови сервис в `backend/services/`.
2. Создай метод в роутере `backend/api/`.
3. Подключи роутер в `main.py` (если новый).
4. Проверь через `/docs`.

### Тестирование

Пока нет автотестов API. Ручное тестирование — через `/docs`.

В планах: `pytest` + `httpx.AsyncClient` для тестов.

### Логирование

Сейчас — только `print` в lifespan. В планах — `loguru` или стандартный `logging`.

---

## Конфигурация

Все настройки — в `.env` в корне проекта:

```
HYPERUM_DB_URL=postgresql://hyperum:hyperum_dev@localhost:5432/hyperum
HYPERUM_NEO4J_URI=bolt://localhost:7687
HYPERUM_NEO4J_USER=neo4j
HYPERUM_NEO4J_PASSWORD=hyperum_dev
HYPERUM_JWT_SECRET=dev-secret-change-me-in-production
HYPERUM_TENANT_DEFAULT=school_lyceum
```

**В продакшне:**
- `HYPERUM_JWT_SECRET` — сгенерировать случайный (`openssl rand -hex 32`).
- Пароли БД — не дефолтные.
- `secure=True` в cookies.

---

## Связанные документы

- `../README.md` — общий обзор проекта
- `../docs/requirements.md` — требования
- `../docs/architecture.md` — архитектура
- `/docs` — OpenAPI (генерируется автоматически)