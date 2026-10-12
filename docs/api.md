# HyperUm — API

**Версия:** 1.0
**Дата:** 2026-10
**Назначение:** обзор REST API. Полная спецификация — в OpenAPI (`/docs`).

**Базовый URL:** `https://hyperum.polyum.ru/api/v1`  
**Локально:** `http://localhost:8000/api/v1`  
**OpenAPI:** `/docs` (Swagger), `/redoc` (ReDoc)

**Связанные документы:**
- `architecture.md` — архитектура
- `data-model.md` — модель данных
- `user-flows.md` — сценарии

---

## 1. Общие принципы

### 1.1. Формат

- **Транспорт:** HTTP/1.1, JSON.
- **Кодировка:** UTF-8.
- **Префикс:** все эндпоинты под `/api/v1`.

### 1.2. Аутентификация

**Два способа одновременно:**

1. **Cookies** (для PWA).
   - `hyperum_access` — access-JWT, 1 час, path `/`.
   - `hyperum_refresh` — refresh-JWT, 30 дней, path `/auth/refresh`.
   - Оба `httpOnly`, `samesite=lax`, `secure=True` в проде.

2. **Bearer-токен** (для интеграций, ПолиУм).
   - `Authorization: Bearer <jwt>`.
   - Возвращается в JSON при `POST /auth/login`.

### 1.3. Роли

| Роль | Доступ |
|------|--------|
| `student` | Свои задания, свой mastery, свой граф, отправка ответов |
| `owner` | Управление классами, генерация тестов, статистика по своим классам |
| `admin` | Всё в tenant'е (в MVP не используется) |
| анонимный | Публичные эндпоинты: лендинг, demo, регистрация по коду |

### 1.4. RLS и tenant

Backend при каждом запросе устанавливает `app.current_tenant` в PostgreSQL. Все данные **изолированы по tenant'у**, кроме shared-таблиц (`tasks`, `task_labels`, `skills`).

### 1.5. Ошибки

Стандартные HTTP-коды:

| Код | Значение |
|-----|----------|
| 200 | OK |
| 201 | Created |
| 400 | Bad Request (валидация) |
| 401 | Unauthorized (нет/невалидный токен) |
| 403 | Forbidden (роль не подходит) |
| 404 | Not Found |
| 409 | Conflict (дубликат) |
| 422 | Unprocessable Entity (Pydantic) |
| 429 | Too Many Requests (rate limit demo) |
| 500 | Internal Server Error |

Формат ошибки:
```json
{"detail": "Текстовое описание"}
```

---

## 2. Эндпоинты по группам

### 2.1. `/health` — системные

| Метод | Путь | Кому | Что |
|-------|------|------|-----|
| GET | `/` | Все | Корневой, ссылки на /docs, /health |
| GET | `/health` | Все | Проверка API |
| GET | `/health/db` | Все | Проверка PostgreSQL + Neo4j |
| GET | `/debug/tenant-test` | Все | Тест RLS (debug) |

**Пример `/health/db`:**
```json
{"postgres": "ok", "neo4j": "ok"}
```

---

### 2.2. `/api/v1/auth` — аутентификация

| Метод | Путь | Кому | Что |
|-------|------|------|-----|
| POST | `/auth/login` | Все | Вход по email + пароль |
| POST | `/auth/logout` | Авторизованные | Очистка cookies |
| POST | `/auth/refresh` | — | Обновление access (**не реализовано**) |
| GET | `/auth/me` | Авторизованные | Профиль + список учеников (для учителя) |

**`POST /auth/login`**

Request:
```json
{"email": "vee4@tpu.ru", "password": "..."}
```

Response:
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

Side effect: устанавливаются cookies `hyperum_access`, `hyperum_refresh`.

**`GET /auth/me`**

Response:
```json
{
  "user": {
    "id": "uuid",
    "tenant_id": "school_lyceum",
    "role": "owner",
    "full_name": "Смирнова Анна Петровна",
    "email": "smirnova@lyceum.ru",
    "created_at": "2026-09-01T10:00:00Z"
  },
  "students": [
    {"id": "uuid", "full_name": "Иванов Иван"}
  ]
}
```

Поле `students` — только для `owner` / `admin`.

---

### 2.3. `/api/v1/groups` — классы

#### Публичные (без авторизации)

| Метод | Путь | Что |
|-------|------|-----|
| GET | `/groups/by-code/{code}` | Информация о классе по коду |
| POST | `/groups/join` | Регистрация ученика по коду |

**`GET /groups/by-code/{code}`**

Response:
```json
{"name": "10А", "subject": "informatics", "teacher_name": "Смирнова А. П."}
```

**`POST /groups/join`**

Request:
```json
{
  "code": "A7K9P2",
  "full_name": "Иванов Иван Иванович",
  "email": "ivanov@lyceum.ru",
  "password": "min6chars"
}
```

Response:
```json
{
  "status": "pending",
  "message": "Заявка отправлена. Учитель подтвердит её в ближайшее время.",
  "group_name": "10А"
}
```

#### Для учителя

| Метод | Путь | Что |
|-------|------|-----|
| POST | `/groups` | Создать класс |
| GET | `/groups` | Список классов учителя |
| GET | `/groups/{id}` | Детали класса (ученики + mastery) |
| PATCH | `/groups/{id}` | Изменить название / предмет |
| POST | `/groups/{id}/regenerate-code` | Новый инвайт-код |
| POST | `/groups/{id}/approve/{sid}` | Подтвердить ученика |
| POST | `/groups/{id}/reject/{sid}` | Отклонить заявку |
| PATCH | `/groups/student/{sid}` | Изменить ФИО ученика |
| DELETE | `/groups/{id}/members/{sid}` | Убрать ученика из класса |

**`GET /groups/{id}`**

Response:
```json
{
  "id": "uuid",
  "name": "10А",
  "subject": "informatics",
  "kind": "class",
  "invite_code": "A7K9P2",
  "created_at": "2026-09-01T10:00:00Z",
  "students_count": 22,
  "pending_count": 2,
  "students": [
    {
      "id": "uuid",
      "full_name": "Иванов Иван",
      "email": "ivanov@lyceum.ru",
      "status": "active",
      "joined_at": "2026-09-05T12:00:00Z",
      "mastery_avg": 0.62,
      "active_assignments": 1,
      "last_completed_title": "Кодирование — 10А",
      "last_completed_score": "4/5",
      "days_since_activity": 2
    }
  ]
}
```

---

### 2.4. `/api/v1/tasks` — банк заданий

| Метод | Путь | Кому | Что |
|-------|------|------|-----|
| GET | `/tasks` | Авторизованные | Список с фильтрами и пагинацией |
| GET | `/tasks/topics` | Авторизованные | Список доступных тем |
| GET | `/tasks/{id}` | Авторизованные | Задание с разметками |
| GET | `/tasks/{id}/labels` | Учитель | Только разметки |

**`GET /tasks?skill_id=s_for&limit=50&offset=0&model=deepseek`**

Response:
```json
{
  "items": [
    {
      "id": "uuid",
      "code": "task_012",
      "text": "...",
      "difficulty": 0.45,
      "skill_id": "s_for"
    }
  ],
  "pagination": {"total": 340, "limit": 50, "offset": 0}
}
```

**`GET /tasks/topics`**

Response:
```json
["Кодирование", "Циклы", "Системы счисления"]
```

---

### 2.5. `/api/v1/mastery` — аналитика освоения

| Метод | Путь | Кому | Что |
|-------|------|------|-----|
| GET | `/mastery/me` | Ученик | Свой mastery |
| GET | `/mastery/student/{id}` | Учитель | Mastery ученика |
| GET | `/mastery/student/{id}/weak?threshold=0.5` | Учитель | Слабые навыки |
| GET | `/mastery/class/{id}` | Учитель | Агрегат класса |
| GET | `/mastery/skills` | Учитель | Сводка по всем навыкам |

**`GET /mastery/me`**

Response:
```json
{
  "student_id": "uuid",
  "full_name": "Иванов Иван",
  "skills": [
    {
      "skill_id": "s_for",
      "skill_name": "Цикл for",
      "mastery": 0.72,
      "attempts": 5,
      "correct": 4,
      "updated_at": "2026-10-10T12:00:00Z"
    }
  ]
}
```

---

### 2.6. `/api/v1/graph` — граф знаний

| Метод | Путь | Кому | Что |
|-------|------|------|-----|
| GET | `/graph/full` | Авторизованные | Полный предметный граф |
| GET | `/graph/student/{id}` | Учитель / сам ученик | Граф с mastery |
| GET | `/graph/class/{id}` | Учитель | Агрегат класса |
| GET | `/graph/skill/{id}?depth=3` | Авторизованные | Подграф вокруг навыка |

**Формат ответа:**
```json
{
  "student_id": "uuid",
  "student_name": "Иванов Иван",
  "nodes": [
    {
      "id": "s_for",
      "name": "Цикл for",
      "module": "Программирование",
      "topic": "Циклы",
      "mastery": 0.72,
      "status": "learning"
    }
  ],
  "edges": [
    {"source": "s_for", "target": "s_nested", "relation": "prerequisite"}
  ]
}
```

**Статусы:** `mastered` (≥0.8), `learning` (0.5–0.8), `weak` (<0.5), `unknown`.

---

### 2.7. `/api/v1/assignments` — генерация и отправка тестов

| Метод | Путь | Кому | Что |
|-------|------|------|-----|
| POST | `/assignments/generate` | Учитель | Preview без сохранения |
| POST | `/assignments/save` | Учитель | Сохранить черновик |
| POST | `/assignments/{id}/send` | Учитель | Отправить ученикам |
| GET | `/assignments` | Учитель | Список своих назначений |
| GET | `/assignments/my` | Ученик | Активные тесты |
| GET | `/assignments/{id}/tasks` | Ученик | Задания (без ответов) |

**`POST /assignments/generate`**

Request:
```json
{"group_id": "uuid", "topic": "Кодирование", "n_tasks": 5}
```

Response:
```json
{
  "class_name": "10А",
  "topic": "Кодирование",
  "n_tasks": 5,
  "students": [
    {
      "student_id": "uuid",
      "full_name": "Иванов Иван",
      "tasks": [
        {
          "task_id": "uuid",
          "code": "task_215",
          "text": "...",
          "skill_id": "s_fano_direct",
          "difficulty": 0.5,
          "mastery": 0.42,
          "score": 0.87
        }
      ],
      "blocked_skills": ["s_fano_reverse"]
    }
  ],
  "usage_stats": {
    "total_tasks_used": 25,
    "unique_tasks_used": 18,
    "max_usage": 3
  }
}
```

**`POST /assignments/save`**

Request:
```json
{
  "title": "Кодирование — 10А",
  "group_id": "uuid",
  "topic": "Кодирование",
  "students": [/* из generate */]
}
```

Response:
```json
{"assignment_id": "uuid", "status": "draft"}
```

**`POST /assignments/{id}/send`**

Response:
```json
{
  "assignment_id": "uuid",
  "status": "sent",
  "students_count": 22,
  "message": "Отправлено 22 ученикам"
}
```

**`GET /assignments/my`** (ученик)

Response:
```json
[
  {
    "id": "uuid",
    "title": "Кодирование — 10А",
    "topic": "Кодирование",
    "status": "sent",
    "student_status": "in_progress",
    "deadline": "2026-10-20T23:59:59Z",
    "task_count": 5,
    "completed_count": 2,
    "created_at": "2026-10-12T10:00:00Z"
  }
]
```

**`GET /assignments/{id}/tasks`** (ученик)

Response:
```json
[
  {
    "position": 1,
    "task_id": "uuid",
    "code": "task_215",
    "text": "...",
    "type": "text",
    "options": null,
    "previous_response": {
      "answer": "111",
      "correct": true,
      "skipped": false,
      "surrendered": false,
      "time_sec": 42,
      "expected": "111"
    }
  }
]
```

**Важно:** `previous_response` — `null`, если ученик ещё не отвечал. Иначе — последний ответ **после `sent_at`** assignment'а.

---

### 2.8. `/api/v1/responses` — ответы учеников

| Метод | Путь | Кому | Что |
|-------|------|------|-----|
| POST | `/responses` | Ученик | Отправить ответ |
| GET | `/responses/my?limit=50&offset=0` | Ученик | История |
| GET | `/responses/task/{id}` | Учитель | Статистика по заданию |
| GET | `/responses/assignment/{id}` | Учитель | Прогресс по назначению |

**`POST /responses`**

Request:
```json
{
  "task_id": "uuid",
  "assignment_id": "uuid",
  "answer": "111",
  "time_sec": 42,
  "skipped": false,
  "surrendered": false
}
```

Response:
```json
{
  "correct": true,
  "expected": "111",
  "explanation": null,
  "new_mastery": 0.78,
  "skipped": false
}
```

**Пропуск / сдача:**
```json
{
  "task_id": "uuid",
  "assignment_id": "uuid",
  "answer": "",
  "skipped": true,
  "surrendered": true
}
```

Response:
```json
{
  "correct": false,
  "expected": null,
  "explanation": null,
  "new_mastery": null,
  "skipped": true
}
```

**Side effects:**
- INSERT в `responses`.
- UPDATE `student_mastery` по всем навыкам задания.
- MERGE `MASTERY` в Neo4j (best-effort).
- Автозакрытие assignment, если всё покрыто.

---

### 2.9. `/api/v1/demo` — демо-режим

Публичные эндпоинты. Авторизация не требуется.

| Метод | Путь | Что |
|-------|------|-----|
| POST | `/demo/start` | Создать demo-сессию |
| POST | `/demo/response` | Ответ гостя |
| GET | `/demo/graph/{session_id}` | Граф гостя |

**`POST /demo/start`**

Request:
```json
{"description": "Я знаю системы счисления, не знаю кодирование изображений"}
```

Response:
```json
{
  "session_id": "uuid",
  "topic": "Кодирование",
  "total_tasks": 5,
  "reasoning": "Гость упомянул слабость в кодировании",
  "tasks": [
    {"task_id": "uuid", "code": "task_215", "text": "...", "position": 1}
  ]
}
```

**Rate limit:** 5 запусков в час по IP. При превышении — 429.

**`POST /demo/response`**

Request:
```json
{"session_id": "uuid", "task_id": "uuid", "answer": "111", "time_sec": 30}
```

Response:
```json
{"correct": true, "expected": "111", "new_mastery": 0.68}
```

**`GET /demo/graph/{session_id}`** — как `/graph/student/{id}`, но для demo-гостя.

---

## 3. Полные сценарии

### 3.1. Учитель генерирует и отправляет тест

```bash
# 1. Логин
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"email":"vee4@tpu.ru","password":"..."}'

# 2. Список классов
curl http://localhost:8000/api/v1/groups -b cookies.txt

# 3. Генерация
curl -X POST http://localhost:8000/api/v1/assignments/generate \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"group_id":"uuid","topic":"Кодирование","n_tasks":5}'

# 4. Сохранение
curl -X POST http://localhost:8000/api/v1/assignments/save \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"title":"Кодирование","group_id":"uuid","topic":"Кодирование","students":[...]}'

# 5. Отправка
curl -X POST http://localhost:8000/api/v1/assignments/{id}/send \
  -b cookies.txt
```

### 3.2. Ученик решает тест

```bash
# 1. Логин
curl -X POST .../auth/login -c cookies.txt -d '{...}'

# 2. Активные тесты
curl .../assignments/my -b cookies.txt

# 3. Задания
curl .../assignments/{id}/tasks -b cookies.txt

# 4. Ответ
curl -X POST .../responses -b cookies.txt \
  -d '{"task_id":"uuid","assignment_id":"uuid","answer":"111","time_sec":42}'

# 5. Граф
curl .../graph/student/{me} -b cookies.txt
```

### 3.3. Demo

```bash
# 1. Старт
curl -X POST .../demo/start \
  -d '{"description":"я знаю системы счисления"}'

# 2. Ответы
curl -X POST .../demo/response \
  -d '{"session_id":"uuid","task_id":"uuid","answer":"111"}'

# 3. Граф
curl .../demo/graph/{session_id}
```

---

## 4. Что НЕ реализовано

| Функция | Приоритет |
|---------|-----------|
| `POST /auth/refresh` | SHOULD |
| Регистрация учителя через API | SHOULD |
| `POST /ingest/csv` | SHOULD |
| WebSocket для real-time | COULD |
| Rate limiting (кроме demo) | COULD |
| Полнотекстовый поиск по заданиям | COULD |
| Редактирование сгенерированного теста | MUST (FR-5.7) |
| Отправка одного задания | MUST (FR-6.8) |

---

## 5. Клиенты

### 5.1. PWA (Axios)

```typescript
const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,   // cookies
  headers: {'Content-Type': 'application/json'},
})
```

### 5.2. Внешние интеграции (ПолиУм)

Использовать **Bearer-токен**:
```
Authorization: Bearer eyJhbGci...
```

Токен получается через `POST /auth/login` и хранится в защищённом месте на стороне интеграции.

---

## 6. Изменения

| Версия | Дата | Что изменилось |
|--------|------|----------------|
| 1.0 | 2026-10 | Первая версия. Отражает все роутеры |