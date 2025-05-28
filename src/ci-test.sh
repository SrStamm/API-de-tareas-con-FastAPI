#!/bin/bash
set -e  # Para que falle si algún comando falla

echo "🚀 Iniciando tests..."

echo "✅ Ejecutando tests"
pytest -q --disable-warnings

echo "🛑 Deteniendo contenedores"
docker compose -f docker-compose.test.yml down

echo "🧹 Limpiando cachés de tests"
find . -type d -name "__pycache__" -exec rm -r {} + && rm -rf .pytest_cache

echo "🏁 Tests finalizados"
