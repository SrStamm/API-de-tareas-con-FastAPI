#! /bin/bash 
echo "Creando con Docker-Compose los contenedores de desarrollo"
docker-compose down

docker-compose -f docker-compose.yml up --build -d
echo "Contenedores para Desarrollo creados!"