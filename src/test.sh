#! /bin/bash
echo "Iniciando Test"
echo "Iniciando Redis:"
docker start redis-stack task-db

pytest -q --disable-warnings

echo "Test terminado"
echo "Cerrando Redis:"
docker stop redis-stack task-db

find . -type d -name "__pycache__" -exec rm -r {} + && rm -rf .pytest_cache
echo "Eliminado cache de tests"