from typing import Dict, List
from fastapi import WebSocket
from .logger import logger
import uuid
from db.database import redis_client
from redis.asyncio import Redis
from models import schemas
from datetime import datetime
import asyncio, json
from tasks import save_notification_in_db
from core.event_ws import format_notification
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
        self.redis = redis
        self.pubsub_tasks: Dict[str, asyncio.Task] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int, project_id: int):
        # Acepta la conexion
        await websocket.accept()

        # Crea el ID connection
        connection_id = str(uuid.uuid4())
        
        # Crea metadata
        metadata = {
            "connection_id": connection_id,
            "user_id": user_id,
            "project_id": project_id,
        }

        # Asigna el hash y set
        await self.redis.set(f"connection:{connection_id}", json.dumps(metadata))
        await self.redis.sadd(f"user_connections:{user_id}", connection_id)
        await self.redis.sadd(f"project_connections:{project_id}", connection_id)
        logger.info(f"[CONNECTED] user={user_id} project={project_id} conn={connection_id}")

        event_connected = schemas.WebSocketEvent(
            type='user_connected',
            payload=schemas.Message(
                user_id=user_id,
                project_id=project_id,
                timestamp=datetime.now(),
                content=f'El usuario {user_id} se ha conectado al projecto {project_id}'
                ).model_dump()
        ).model_dump_json()

        await websocket.send_json(event_connected)

        # Iniciar la subscripción a canales
        await self._subscribe(websocket, user_id, project_id, connection_id)
        return connection_id

    async def _subscribe(self, websocket: WebSocket, user_id: int, project_id: int, connection_id: str):
        # Subscribe a los canales
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(f"user:{user_id}", f"project:{project_id}")
        logger.info(f"Subscribed user={user_id} to channels user:{user_id} and project:{project_id}")

        async def reader():
            try:
                while True:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message.get("data"):
                        data = message["data"].decode()
                        try:
                            await websocket.send_text(data)
                            logger.info(f"Sent message to WebSocket user={user_id} conn={connection_id}: {data}")
                        except Exception as e:
                            logger.error(f"Failed to send message to WebSocket user={user_id} conn={connection_id}: {str(e)}")
            except Exception as e:
                logger.error(f"Error in Pub/Sub reader for user={user_id} conn={connection_id}: {str(e)}")
            finally:
                await pubsub.unsubscribe(f"user:{user_id}", f"project:{project_id}")
                logger.info(f"Unsubscribed user={user_id} conn={connection_id} from Pub/Sub")
        
        # Iniciar tarea de lectura en segundo plano
        self.pubsub_tasks[connection_id] = asyncio.create_task(reader())

    async def disconnect(self, connection_id: str):
        # Obtiene la conexion
        raw = await self.redis.get(f"connection:{connection_id}")
        if raw:
            # Desencripta y obtiene sus datos
            metadata = json.loads(raw)
            user_id = metadata["user_id"]
            project_id = metadata["project_id"]

            # Elimina las conexiones
            await self.redis.delete(f"connection:{connection_id}")
            await self.redis.srem(f"user_connections:{user_id}", connection_id)
            await self.redis.srem(f"project_connections:{project_id}", connection_id)
            logger.info(f"Removed from Redis: conn={connection_id}, user={user_id}, project={project_id}")
        
        # Cancelar la subscripcion si existe
        if connection_id in self.pubsub_tasks:
            self.pubsub_tasks[connection_id].cancel()
            del self.pubsub_tasks[connection_id]
            logger.info(f"Cancelled Pub/Sub task for conn={connection_id}")
        logger.info(f"[DISCONNECTED] conn={connection_id}")

    async def send_to_user(self, user_id: int, message: dict):
        connected = await self.redis.exists(f"user_connections:{user_id}")

        if connected:
            json_message = format_notification(
                notification_type=message["notification_type"],
                message=message["message"]
            )

            await self.redis.publish(f"user:{user_id}", json_message)
            logger.info(f"[send_to_user] Published message to user:{user_id}: {json_message}")
        else:
            logger.warning(f'User {user_id} not connected.')
            save_notification_in_db.delay(message=message, user_id=user_id)

    async def broadcast(self, project_id: int, message: str):
        await self.redis.publish(f"project:{project_id}", message)
        logger.info(f"Published broadcast to project:{project_id}: {message}")

manager = RedisConnectionManager(redis_client)