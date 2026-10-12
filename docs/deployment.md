# HyperUm — Развёртывание

**Версия:** 1.0
**Дата:** 2026-10
**Назначение:** описать полный цикл развёртывания системы: локально и на VPS.

**Связанные документы:**
- `architecture.md` — архитектура
- `README.md` (root) — быстрый старт
- `backend/README.md` — API

---

## 1. Окружения

| Окружение | Где | Назначение | Домен |
|-----------|-----|-----------|-------|
| **dev** | Локальная машина (Windows) | Разработка | `localhost:8000` / `localhost:5173` |
| **prod** | VPS | Пилот + демо | `hyperum.polyum.ru` |

**Промежуточных окружений (staging) нет.** Изменения деплоятся напрямую в prod. Это допустимо для одного разработчика и одного пилота.

---

## 2. Локальная разработка (dev)

### 2.1. Требования

- Python 3.11+
- Node.js 20+
- Docker Desktop
- Git

### 2.2. Первый запуск

```powershell
# 1. Клонирование
git clone <repo-url> hyperum
cd hyperum

# 2. venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# если политика запрещает:
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 3. Зависимости backend
pip install -r requirements-backend.txt

# 4. .env
Copy-Item .env.example .env
# отредактировать: HYPERUM_DB_URL, NEO4J_*, JWT_SECRET, DEEPSEEK_API_KEY

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
# + задачи из tasks/*.csv

# 9. Разметка
python -m ml.label_tasks_with_deepseek
python -m ml.normalize_difficulty

# 10. Учитель
python -m scripts.set_password vee4@tpu.ru mypassword
```

### 2.3. Запуск на каждый раз

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

**Терминал 3 (или фон) — Docker:**
```powershell
docker compose up -d
```

**Проверка:**
- API: http://localhost:8000/docs
- Health: http://localhost:8000/health/db
- PWA: http://localhost:5173
- Neo4j Browser: http://localhost:7474

### 2.4. Vite-прокси

В `pwa/vite.config.ts`:
```typescript
server: {
  proxy: {
    '/api': { target: 'http://localhost:8000', changeOrigin: true }
  }
}
```

Все запросы `/api/v1/*` из PWA проксируются на backend. Cookies работают без CORS-проблем.

### 2.5. CORS

В `backend/main.py`:
```python
allow_origins=[
    "http://localhost:5173",  # PWA dev
    "http://localhost:3000",  # альтернативный порт
    "http://localhost:8501",  # Streamlit (legacy)
]
```

---

## 3. Prod (VPS)

### 3.1. Требования

- VPS с Ubuntu 22.04+ (или Debian).
- Домен `hyperum.polyum.ru`.
- Docker + Docker Compose.
- Nginx.
- Доступ по SSH.

### 3.2. Структура на VPS

```
/root/hyperum/                 # репозиторий
├── .env                       # секреты (не в git)
├── docker-compose.prod.yml
├── backend/
├── pwa/
│   └── dist/                  # собранный фронт
└── ...
```

### 3.3. `.env` на VPS

Отличается от dev:

```
POSTGRES_USER=hyperum
POSTGRES_PASSWORD=<случайный>
POSTGRES_DB=hyperum

HYPERUM_DB_URL=postgresql+psycopg://hyperum:<pwd>@postgres:5432/hyperum
HYPERUM_NEO4J_URI=bolt://neo4j:7687
HYPERUM_NEO4J_USER=neo4j
HYPERUM_NEO4J_PASSWORD=<случайный>

HYPERUM_JWT_SECRET=<openssl rand -hex 32>
HYPERUM_TENANT_DEFAULT=school_lyceum
HYPERUM_DEBUG=false

DEEPSEEK_API_KEY=<ключ>
```

**Правила:**
- Пароли — не дефолтные.
- `JWT_SECRET` — случайный, не `dev-secret-change-me`.
- `HYPERUM_DEBUG=false`.
- Секреты **не коммитятся**.

### 3.4. Docker Compose (prod)

`docker-compose.prod.yml`:

```yaml
services:
  postgres:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks: [hyperum]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  neo4j:
    image: neo4j:5
    restart: unless-stopped
    environment:
      NEO4J_AUTH: ${NEO4J_USER}/${NEO4J_PASSWORD}
      NEO4J_server_memory_heap_initial__size: 256m
      NEO4J_server_memory_heap_max__size: 384m
      NEO4J_server_memory_pagecache_size: 256m
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    networks: [hyperum]

  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    restart: unless-stopped
    env_file: .env
    environment:
      HYPERUM_DB_URL: postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      HYPERUM_NEO4J_URI: bolt://neo4j:7687
    depends_on:
      postgres: {condition: service_healthy}
      neo4j:    {condition: service_started}
    ports:
      - "127.0.0.1:8000:8000"     # слушает только localhost
    networks: [hyperum]

networks:
  hyperum:

volumes:
  postgres_data:
  neo4j_data:
  neo4j_logs:
```

**Ключевое:**
- Backend слушает **только `127.0.0.1:8000`** — снаружи доступ через Nginx.
- Postgres и Neo4j — только внутри docker-сети.
- Volume'ы персистентны.

### 3.5. Backend Dockerfile

`backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Только backend-зависимости (без streamlit/plotly/matplotlib)
COPY requirements-backend.txt .
RUN pip install --no-cache-dir -r requirements-backend.txt

# Код проекта
COPY backend/ ./backend/
COPY ml/ ./ml/
COPY ingest/ ./ingest/
COPY scripts/ ./scripts/
COPY taxonomy/ ./taxonomy/
COPY migrations/ ./migrations/
COPY tasks/ ./tasks/

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Ключевое:**
- `python:3.11-slim` — минимальный образ.
- `requirements-backend.txt` — только backend. **Не** тянет streamlit, plotly, matplotlib → образ ~200 MB вместо ~1.5 GB.
- Копируются только нужные папки.
- Без `--reload` в CMD (prod).

### 3.6. Nginx

Конфиг **вне репозитория**. Пример:

```nginx
server {
    listen 443 ssl http2;
    server_name hyperum.polyum.ru;

    ssl_certificate     /etc/letsencrypt/live/hyperum.polyum.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hyperum.polyum.ru/privkey.pem;

    # PWA (статика)
    root /var/www/hyperum;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;   # SPA fallback
    }

    # API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Swagger (опционально закрыть)
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
    }
}

server {
    listen 80;
    server_name hyperum.polyum.ru;
    return 301 https://$host$request_uri;
}
```

**Ключевое:**
- HTTPS (Let's Encrypt).
- `try_files ... /index.html` — SPA-роутинг.
- `X-Forwarded-For` — чтобы `_client_ip` в demo работал правильно.
- HTTP → HTTPS редирект.

### 3.7. PWA (сборка)

```bash
cd pwa
npm install
npm run build
# результат — pwa/dist/
```

Скопировать `pwa/dist/*` в `/var/www/hyperum/` на VPS.

**В проде PWA обращается к `/api/v1`** — тот же origin, поэтому CORS не нужен, cookies работают через `same-origin`.

### 3.8. Обновление (deploy)

`scripts/deploy.sh`:

```bash
#!/bin/bash
set -e

echo "=== Git pull ==="
git pull

echo "=== Rebuild backend ==="
docker compose -f docker-compose.prod.yml build backend

echo "=== Restart ==="
docker compose -f docker-compose.prod.yml up -d

echo "=== Health check ==="
sleep 5
curl -s http://localhost:8000/health/db

echo "✓ Deploy завершён"
```

**Что делает:**
1. Тянет изменения из git.
2. Пересобирает **только backend** (PWA собирается отдельно и копируется руками).
3. Перезапускает контейнеры.
4. Проверяет health.

**Что НЕ делает:**
- Не применяет миграции (запускаются отдельно).
- Не собирает PWA.
- Не делает бэкап.

### 3.9. Обновление PWA

```bash
# Локально
cd pwa
npm run build

# Скопировать dist на сервер
scp -r pwa/dist/* root@vps:/var/www/hyperum/

# На VPS
systemctl reload nginx
```

### 3.10. Миграции

```bash
# На VPS
docker exec -i hyperum_postgres psql -U hyperum -d hyperum < migrations/NNN_name.sql
```

Или через PowerShell-скрипт (если сервер Windows — но у нас Linux).

**Важно:** миграции идемпотентны. Можно применять повторно.

---

## 4. Бэкапы

**Статус:** ⚠️ **Не реализовано.** Критично.

### 4.1. Что нужно сделать

**PostgreSQL:**
```bash
# Ручной дамп
docker exec hyperum_postgres pg_dump -U hyperum hyperum > backup_$(date +%Y%m%d).sql

# Восстановление
docker exec -i hyperum_postgres psql -U hyperum hyperum < backup_20261011.sql
```

**Neo4j:**
```bash
# Ręczny dump (пока Neo4j запущен — через APOC)
# или остановить и скопировать volume
docker run --rm -v hyperum_neo4j_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/neo4j_$(date +%Y%m%d).tar.gz -C /data .
```

**Cron на VPS:**
```cron
0 3 * * * /root/hyperum/scripts/backup.sh
```

**Хранение:** локально + на удалённом хранилище (S3, Яндекс.Диск).

**План:** реализовать в ноябре 2026 (F56).

### 4.2. Что бэкапить в первую очередь

1. **PostgreSQL** — все данные пилота. Критично.
2. **Neo4j** — только структура графа. Восстанавливается из YAML + скриптов.
3. **`.env`** — секреты. Отдельно, не в публичном хранилище.

**Neo4j не критичен:** можно восстановить через `ml/load_taxonomy.py` + `ml/sync_mastery_to_neo4j.py`.

---

## 5. Мониторинг

**Статус:** ⚠️ Минимальный. Только `/health/db` и логи Docker.

### 5.1. Что есть

- `docker compose ps` — статус контейнеров.
- `docker compose logs -f backend` — логи backend.
- `/health/db` — проверка соединений.
- `/docs` — Swagger для ручных проверок.

### 5.2. Что нужно

- **Uptime-мониторинг** (UptimeRobot, self-hosted Uptime Kuma).
- **Логи** через `loguru` или стандартный `logging` (сейчас только `print`).
- **Алерты** при падении.
- **Метрики** запросов (latency, error rate).

**Приоритет:** COULD. Не блокирует пилот.

---

## 6. Безопасность (prod)

### 6.1. Чеклист перед продом

- [x] HTTPS через Let's Encrypt.
- [x] Backend слушает только `127.0.0.1:8000`.
- [x] Postgres и Neo4j — в изолированной docker-сети.
- [x] Пароли БД — не дефолтные.
- [x] `JWT_SECRET` — случайный.
- [x] `HYPERUM_DEBUG=false`.
- [ ] **`secure=True` в cookies** — ⚠️ сейчас False.
- [ ] Rate limiting (кроме demo).
- [ ] Firewall (ufw) — только 22, 80, 443.
- [ ] Fail2ban на SSH.

### 6.2. Критично исправить

**Cookies `secure=True`:**

В `backend/api/auth.py`:
```python
COOKIE_COMMON = {
    "httponly": True,
    "secure": True,           # ← было False
    "samesite": "lax",
}
```

После правки — задеплоить и проверить, что login работает через HTTPS.

### 6.3. 152-ФЗ

- PII хранится на территории РФ (VPS в РФ).
- Согласия родителей — организационная задача.
- Возможность удаления аккаунта — не реализовано.
- Логирование доступа к PII — не реализовано.

---

## 7. Troubleshooting

| Проблема | Причина | Решение |
|----------|---------|---------|
| 502 Bad Gateway | Backend упал | `docker compose logs backend` |
| Пустая страница PWA | SPA fallback не работает | Проверить `try_files` в Nginx |
| CORS error | Origin не в списке | Добавить в `allow_origins` |
| Cookies не ставятся | `secure=True` при HTTP | Логин по HTTPS |
| Neo4j долго стартует | Heap 30 сек | Подождать, проверить `docker compose ps` |
| Psql permission denied | RLS не установлен | `tenant_session()` решает |
| Кириллица в psql квадратиками | Кодировка терминала | Использовать `run_sql.ps1` |

---

## 8. Дорожная карта инфраструктуры

| Период | Что | Приоритет |
|--------|-----|-----------|
| Октябрь 2026 | Бэкапы БД (F56) | MUST |
| Октябрь 2026 | `secure=True` в cookies | MUST |
| Ноябрь 2026 | Uptime-мониторинг | SHOULD |
| Ноябрь 2026 | Логирование через `logging`/`loguru` | SHOULD |
| Декабрь 2026 | Rate limiting через Redis | SHOULD |
| Январь 2027 | CI/CD (GitHub Actions) | COULD |

---

## 9. Изменения

| Версия | Дата | Что изменилось |
|--------|------|----------------|
| 1.0 | 2026-10 | Первая версия. Dev, prod, VPS hyperum.polyum.ru |