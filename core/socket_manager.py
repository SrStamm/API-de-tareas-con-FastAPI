from typing import Dict, List
from fastapi import WebSocket
from .logger import logger
from uuid import uuid4
import json
from db.database import redis_client
from redis.asyncio import Redis
class ConnectionManager:
    # Crea una lista de conexiones activas
    def __init__(self):
        # Conexiones por proyecto
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # Conexiones por usuario
        self.active_users_connections: Dict[int, List[WebSocket]] = {}

    # Conecta el usuario a ws y lo agrega a la lista de conexiones activas
    async def connect(self, websocket: WebSocket, project_id: int, user_id:int):
        await websocket.accept()
        
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)

        if user_id not in self.active_users_connections:
            self.active_users_connections[user_id] = []
        self.active_users_connections[user_id].append(websocket)

    # Desconecta y elimina el usuario de conexiones
    def disconnect(self, websocket: WebSocket, project_id: int, user_id: int):
        # Elimina conexiones por proyecto
        if project_id in self.active_connections:
            self.active_connections[project_id].remove(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
        
        # Elimina conexiones por usuario
        if user_id in self.active_users_connections:
            self.active_users_connections[user_id].remove(websocket)
            if not self.active_users_connections[user_id]:
                del self.active_users_connections[user_id]

    # Envia un mensaje personal
    async def send_to_user(self, message_json_string: str, user_id: int):
        if user_id in self.active_users_connections:
            connections_to_send = list(self.active_users_connections[user_id])
            for connection in connections_to_send:
                try:
                    await connection.send_text(message_json_string)
                except Exception:
                    logger.error(f'Fallo al enviar mensaje al websocket de usuario {user_id}. La conexión podría no estar activa')

    async def broadcast(self, message_json_string: str, project_id: int):
        if project_id in self.active_connections:
            connections_to_send = list(self.active_connections[project_id])
            for connection in connections_to_send:
                try:
                    await connection.send_text(message_json_string)
                except Exception:
                    logger.error(f'Fallo al broadcast a websocket en proyecto {project_id}. La conexión podría no estar activa')

# manager = ConnectionManager()

class RedisConnectionManager:
    def __init__(self, redis: Redis):
        self.redis: Redis = redis
        self.local_Ws: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id:int, project_id: int):
        await websocket.accept()
        
        # Crear un ID de conexión
        connection_id = str(uuid4())
        
        # Creando el JSON que contiene la información
        metadata = {
            "connection_id":connection_id,
            "user_id":user_id,
            "project_id":project_id,
            }

        # 1. Guardar en Redis
        await self.redis.set(f"connection:{connection_id}", json.dumps(metadata))
        await self.redis.sadd(f"user_connections:{user_id}", connection_id)
        await self.redis.sadd(f"project_connections:{project_id}", connection_id)

        # 2. Guardar localmente
        self.local_Ws[connection_id] = websocket

        logger.info(f"[CONNECTED] user={user_id} project={project_id} conn={connection_id}")
        return connection_id

    async def disconnect(self, connection_id: str):
        # 1. Eliminar de redis
        raw = await self.redis.get(f"connection:{connection_id}")
        
        if raw:
            metadata = json.loads(raw)
            user_id = metadata["user_id"]
            project_id = metadata["project_id"]

            await self.redis.delete(f"connection:{connection_id}")
            await self.redis.srem(f"user_connections:{user_id}")
            await self.redis.srem(f"project_connections:{project_id}")
        
        # 2. Eliminar de local
        self.local_Ws.pop[connection_id, None]
        logger.info(f"[DISCONNECTED] conn={connection_id}")

    async def send_to_user(self, user_id: int, message: str):
        conn_ids = await self.redis.smembers(f"user_connections:{user_id}")
        for conn_id in conn_ids:
            ws = self.local_Ws.get(conn_id)
            if ws:
                try:
                    await ws.send_text(message)
                except Exception:
                    logger.error(f"Fallo al enviar mensaje a {conn_id} (user={user_id})")

    async def broadcast(self, project_id: int, message: str):
        conn_ids = await self.redis.smembers(f"project_connections:{project_id}")
        for conn_id in conn_ids:
            ws = self.local_Ws.get(conn_id)
            if ws:
                try:
                    await ws.send_text(message)
                except Exception:
                    logger.error(f"Fallo al enviar broadcast a {conn_id} (project={project_id})")

manager = RedisConnectionManager(redis_client)