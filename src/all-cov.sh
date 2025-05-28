#! /bin/bash 
echo "Iniciando"

rm -r htmlcov/

echo "Iniciando Redis:"
docker start redis-stack

source env/bin/activate
pytest --cov=. --cov-report=html

echo "Test terminado"
echo "Cerrando Redis:"

docker stop redis-stack

echo "Eliminado cache de tests"

echo "Abriendo resultado"
xdg-open htmlcov/index.html