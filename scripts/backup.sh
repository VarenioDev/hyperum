#!/bin/bash
# ============================================================
# HyperUm — Backup
# Бэкапит PostgreSQL + конфиги. Ротация daily/weekly/monthly.
#
# Запуск:  ./scripts/backup.sh
# Cron:    0 3 * * * /root/hyperum/scripts/backup.sh >> /var/log/hyperum_backup.log 2>&1
# ============================================================

set -euo pipefail

# ─── Конфигурация ─────────────────────────────────────────
BACKUP_ROOT="${BACKUP_ROOT:-/root/hyperum_backups}"
PROJECT_ROOT="${PROJECT_ROOT:-/root/hyperum}"

KEEP_DAILY=7
KEEP_WEEKLY=4
KEEP_MONTHLY=12
MIN_FREE_MB=500

PG_CONTAINER="hyperum_postgres"
PG_USER="hyperum"
PG_DB="hyperum"
ENV_FILE="${PROJECT_ROOT}/.env"
NGINX_CONF="/etc/nginx/sites-available/hyperum"

# ─── Хелперы ──────────────────────────────────────────────
log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"; }
die() { log "ОШИБКА: $*"; exit 1; }

# ─── Старт ────────────────────────────────────────────────
log "=== Backup started ==="

[ -d "$PROJECT_ROOT" ] || die "PROJECT_ROOT not found: $PROJECT_ROOT"
[ -f "$ENV_FILE" ] || log "WARN: .env not found: $ENV_FILE"

command -v docker >/dev/null || die "docker not found"
docker ps --format '{{.Names}}' | grep -q "^${PG_CONTAINER}$" \
    || die "Container $PG_CONTAINER is not running"

# ─── Место на диске ───────────────────────────────────────
mkdir -p "$BACKUP_ROOT"
FREE_MB=$(df -m "$BACKUP_ROOT" | awk 'NR==2 {print $4}')
[ "$FREE_MB" -ge "$MIN_FREE_MB" ] || die "Low disk space: ${FREE_MB}MB < ${MIN_FREE_MB}MB"
log "Free space: ${FREE_MB}MB"

# ─── Директории ───────────────────────────────────────────
DAY=$(date +%Y-%m-%d)
WEEK=$(date +%Y-W%V)
MONTH=$(date +%Y-%m)

DAILY_DIR="$BACKUP_ROOT/daily/$DAY"
WEEKLY_DIR="$BACKUP_ROOT/weekly/$WEEK"
MONTHLY_DIR="$BACKUP_ROOT/monthly/$MONTH"

mkdir -p "$DAILY_DIR"

# ─── 1. PostgreSQL ────────────────────────────────────────
log "Dumping PostgreSQL..."
PG_DUMP_FILE="$DAILY_DIR/postgres.dump"

docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -Fc -d "$PG_DB" \
    > "$PG_DUMP_FILE" || die "pg_dump failed"

# Проверка, что дамп непустой
PG_SIZE=$(stat -c %s "$PG_DUMP_FILE" 2>/dev/null || stat -f %z "$PG_DUMP_FILE")
[ "$PG_SIZE" -gt 1024 ] || die "pg_dump produced too small file: ${PG_SIZE}B"
log "PostgreSQL dumped: $(du -h "$PG_DUMP_FILE" | cut -f1)"

# ─── 2. Конфиги ───────────────────────────────────────────
log "Copying configs..."
[ -f "$ENV_FILE" ] && cp "$ENV_FILE" "$DAILY_DIR/env.backup" && log "  .env"
[ -f "$NGINX_CONF" ] && cp "$NGINX_CONF" "$DAILY_DIR/nginx-hyperum.conf" && log "  nginx"
[ -f "$PROJECT_ROOT/docker-compose.prod.yml" ] && \
    cp "$PROJECT_ROOT/docker-compose.prod.yml" "$DAILY_DIR/" && \
    log "  docker-compose.prod.yml"

# ─── 3. Метаданные ────────────────────────────────────────
cat > "$DAILY_DIR/meta.txt" <<EOF
Backup date: $(date +'%Y-%m-%d %H:%M:%S %Z')
Hostname:    $(hostname)
Project:     HyperUm
PostgreSQL:  $PG_DB
Git commit:  $(cd "$PROJECT_ROOT" && git rev-parse --short HEAD 2>/dev/null || echo "n/a")

Docker containers:
$(docker ps --format '  {{.Names}} ({{.Status}})')
EOF
log "Metadata written"

# ─── 4. Rotation ──────────────────────────────────────────
# Sunday → weekly
if [ "$(date +%u)" = "7" ]; then
    mkdir -p "$WEEKLY_DIR"
    cp -r "$DAILY_DIR"/* "$WEEKLY_DIR/"
    log "Copied to weekly: $WEEKLY_DIR"
fi

# 1st day of month → monthly
if [ "$(date +%d)" = "01" ]; then
    mkdir -p "$MONTHLY_DIR"
    cp -r "$DAILY_DIR"/* "$MONTHLY_DIR/"
    log "Copied to monthly: $MONTHLY_DIR"
fi

# ─── 5. Cleanup ───────────────────────────────────────────
cleanup() {
    local dir=$1
    local keep=$2
    [ -d "$dir" ] || return 0

    local count
    count=$(find "$dir" -mindepth 1 -maxdepth 1 -type d | wc -l)

    if [ "$count" -gt "$keep" ]; then
        local to_delete=$((count - keep))
        log "Cleanup $dir: removing $to_delete of $count"
        find "$dir" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' \
            | sort -n | head -n "$to_delete" | awk '{print $2}' \
            | xargs -r rm -rf
    fi
}

cleanup "$BACKUP_ROOT/daily"   "$KEEP_DAILY"
cleanup "$BACKUP_ROOT/weekly"  "$KEEP_WEEKLY"
cleanup "$BACKUP_ROOT/monthly" "$KEEP_MONTHLY"

# ─── 6. Итог ──────────────────────────────────────────────
TOTAL_SIZE=$(du -sh "$DAILY_DIR" | cut -f1)
log "Backup completed: $DAILY_DIR ($TOTAL_SIZE)"
log "=== Backup finished ==="