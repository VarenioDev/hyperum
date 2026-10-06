#!/bin/bash
# Deploy на VPS. Запускать из /root/hyperum.
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

echo ""
echo "✓ Deploy завершён"