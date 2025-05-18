#! /bin/bash 
echo "Iniciando cov"

echo "Iniciando Redis:"
docker start redis-stack

pytest --cov=./routers --cov-report=html

echo "Test terminado"
echo "Cerrando Redis:"

docker stop redis-stack

echo "Abriendo resultado"

xdg-open htmlcov/index.html