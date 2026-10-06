FROM python:3.11-slim

WORKDIR /app

# Минимальные системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Только backend-зависимости (без streamlit/plotly/matplotlib)
COPY requirements-backend.txt .
RUN pip install --no-cache-dir -r requirements-backend.txt

# Код проекта
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
