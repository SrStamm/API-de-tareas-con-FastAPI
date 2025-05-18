#! /bin/bash
echo "Conexión entorno virtual"
source env/bin/activate

docker start task-db redis-stack

uvicorn main:app --reload

docker stop task-db redis-stack

echo "Desconexión entorno virtual"
deactivate