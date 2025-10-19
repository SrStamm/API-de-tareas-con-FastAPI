#!/bin/bash
# Activar entorno virtual
source env/bin/activate

echo "🚀 Iniciando tests..."

echo "📦 Levantando contenedores de Redis"
docker start redis-stack

echo "🔍 Ejecutando Pytest"
pytest -vv --disable-warnings

echo "✅ Test finalizados correctamente"

echo "🛑 Deteniendo contenedores"
docker stop redis-stack task-db
