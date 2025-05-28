#!/bin/bash
set -e  # Para que falle si algún comando falla

echo "🚀 Iniciando tests..."

echo "📦 Levantando contenedores desde docker-compose.test.yml"
docker compose -f docker-compose.test.yml up --build -d

echo "⏱ Esperando servicios..."
sleep 5

echo "✅ Ejecutando tests"
pytest -q --disable-warnings

echo "🛑 Deteniendo contenedores"
docker compose -f docker-compose.test.yml down

echo "🧹 Limpiando cachés de tests"
find . -type d -name "__pycache__" -exec rm -r {} + && rm -rf .pytest_cache

echo "🏁 Tests finalizados"
