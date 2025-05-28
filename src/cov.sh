#! /bin/bash 
echo "Iniciando cov"

rm -r htmlcov/

echo "Iniciando Redis:"
docker start redis-stack

source env/bin/activate
pytest --cov=./api/v1 --cov-report=html

echo "Test terminado"
echo "Cerrando Redis:"

docker stop redis-stack

find . -type d -name "__pycache__" -exec rm -r {} + && rm -rf .pytest_cache
echo "Eliminado cache de tests"

echo "Abriendo resultado"
xdg-open htmlcov/index.html