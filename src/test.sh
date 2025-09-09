#!/bin/bash
# set -e # <- 🔒 Termina el script si ocurre un error

# Activar entorno virtual
source env/bin/activate || echo "No se pudo activar el entorno virtual, probablemente en CI"

echo "🚀 Iniciando tests..."

echo "📦 Levantando contenedores de Redis"
docker start redis-stack

echo "🔍 Ejecutando Pytest"
pytest -q --disable-warnings

echo "✅ Test finalizados correctamente"

echo "🛑 Deteniendo contenedores"
docker stop redis-stack task-db

echo "🧹 Eliminando cachés de tests"
# find . -type d -name "__pycache__" -exec rm -r {} + && rm -rf .pytest_cache
