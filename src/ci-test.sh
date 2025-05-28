#!/bin/bash
set -e  # Para que falle si algún comando falla

echo "🚀 Iniciando tests..."

echo "📦 Levantando contenedores desde docker-compose.test.yml"
# docker compose -f docker-compose.test.yml up --build -d
docker run --name task-db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=amaterasu -e POSTGRES_DB=database -p 5432:5432 -d postgres:latest
docker run -d --name redis-stack -p 6379:6379 redis/redis-stack:latest

echo "⏱ Esperando servicios..."
sleep 5

echo "✅ Ejecutando tests"
pytest -q --disable-warnings

echo "🛑 Deteniendo contenedores"
docker compose -f docker-compose.test.yml down

echo "🧹 Limpiando cachés de tests"
find . -type d -name "__pycache__" -exec rm -r {} + && rm -rf .pytest_cache

echo "🏁 Tests finalizados"
