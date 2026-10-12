#!/bin/bash
# ============================================================
# HyperUm — Restore PostgreSQL
# Восстанавливает БД из дампа. ПЕРЕЗАПИШЕТ текущие данные.
#
# Использование:
#   ./scripts/restore.sh /root/hyperum_backups/daily/2026-10-12
# ============================================================

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Использование: $0 <backup_dir>"
    echo "Пример:       $0 /root/hyperum_backups/daily/2026-10-12"
    exit 1
fi

BACKUP_DIR="$1"
PG_DUMP="$BACKUP_DIR/postgres.dump"

PG_CONTAINER="hyperum_postgres"
PG_USER="hyperum"
PG_DB="hyperum"

[ -f "$PG_DUMP" ] || { echo "Не найден $PG_DUMP"; exit 1; }

echo "⚠  ВНИМАНИЕ: это ПЕРЕЗАПИШЕТ базу $PG_DB!"
echo "   Дамп: $PG_DUMP ($(du -h "$PG_DUMP" | cut -f1))"
echo ""
read -p "Продолжить? Введите 'yes' для подтверждения: " confirm

[ "$confirm" = "yes" ] || { echo "Отменено."; exit 0; }

echo "1. Останавливаем backend..."
docker stop hyperum_backend || true

echo "2. Восстанавливаем PostgreSQL..."
docker exec -i "$PG_CONTAINER" pg_restore \
    -U "$PG_USER" \
    -d "$PG_DB" \
    --clean --if-exists --no-owner \
    < "$PG_DUMP" || echo "   (некоторые предупреждения могут быть проигнорированы)"

echo "3. Запускаем backend..."
docker start hyperum_backend

echo "4. Ждём 5 секунд..."
sleep 5

echo "5. Проверка /health/db..."
curl -s http://localhost:8000/health/db || echo "   backend ещё не готов"

echo ""
echo "✓ Восстановление завершено."
echo ""
echo "Если потерял Neo4j — восстанови так:"
echo "  cd /root/hyperum"
echo "  python -m ml.load_taxonomy"
echo "  python -m ml.sync_mastery_to_neo4j"