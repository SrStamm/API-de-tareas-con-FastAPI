from typing import Dict, List
from fastapi import WebSocket
from .logger import logger
from db.database import redis_client, sessionlocal
from redis.asyncio import Redis
from tasks import save_notification_in_db, get_pending_notifications_for_user
from core.event_ws import format_notification
import asyncio
import json
import uuid

from sqlmodel import select
from models.db_models import Project, project_user, Notify_State


class RedisConnectionManager:
    def __init__(
        self,
        redis: Redis,
    ):
        self.redis = redis
        self.pubsub_tasks: Dict[str, asyncio.Task] = {}

    async def _subscribe(
        self,
        websocket: WebSocket,
        user_id: int,
        project_ids: List[int],
        connection_id: str,
    ):
        pubsub = self.redis.pubsub()  # Añadir await

        # Crea una lista de canales, incluyendo el canal personal y los de los proyectos
        channels_to_subscribe = [f"user:{user_id}"] + [
            f"project:{p_id}" for p_id in project_ids
        ]

        await pubsub.subscribe(*channels_to_subscribe)
        logger.info(f"Subscribed user={user_id} to channels {channels_to_subscribe}")

        async def reader():
            try:
                while True:
                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                    if message and message.get("data"):
                        data = message["data"].decode()
                        try:
                            await websocket.send_text(data)
                            logger.info(
                                f"Sent message to WebSocket user={user_id} conn={connection_id}: {data}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to send message to WebSocket user={user_id} conn={connection_id}: {str(e)}"
                            )
                            break
            except Exception as e:
                logger.error(
                    f"Error in Pub/Sub reader for user={user_id} conn={connection_id}: {str(e)}"
                )
            finally:
                await pubsub.unsubscribe(*channels_to_subscribe)
                logger.info(
                    f"Unsubscribed user={user_id} conn={connection_id} from Pub/Sub"
                )

        self.pubsub_tasks[connection_id] = asyncio.create_task(reader())

    async def disconnect(self, connection_id: str):
        raw = await self.redis.get(f"connection:{connection_id}")
        if raw:
            metadata = json.loads(raw)
            user_id = metadata["user_id"]

            # Obtiene la lista de IDs de proyectos
            projects_ids = metadata.get("project_ids", [])

            await self.redis.delete(f"connection:{connection_id}")
            await self.redis.srem(f"user_connections:{user_id}", connection_id)

            # Itera sobre la lista para eliminar la conexión de todos los proyectos
            for p_id in projects_ids:
                await self.redis.srem(f"project_connections:{p_id}", connection_id)

            logger.info(
                f"Removed from Redis: conn={connection_id}, user={user_id}, projects={projects_ids}"
            )

        if connection_id in self.pubsub_tasks:
            self.pubsub_tasks[connection_id].cancel()
            del self.pubsub_tasks[connection_id]
            logger.info(f"Cancelled Pub/Sub task for conn={connection_id}")
        logger.info(f"[DISCONNECTED] conn={connection_id}")

    async def send_to_user(self, message: str, user_id: int):
        connected = await self.redis.exists(f"user_connections:{user_id}")
        if connected:
            logger.info(f"message: {message}")

            await self.redis.publish(f"user:{user_id}", message)
        else:
            logger.warning(f"User {user_id} not connected.")
            save_notification_in_db.delay(message=message, user_id=user_id)

    async def broadcast(self, message: str, project_id: int):
        await self.redis.publish(f"project:{project_id}", message)
        logger.info(f"Published broadcast to project:{project_id}: {message}")

    async def connect_to_user_projects(self, websocket, user_id: int, session):
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        logger.info(f"[CONNECTED] user={user_id} conn={connection_id}")

        # Obtiene todos los IDs de los proyectos a los que pertenece el usuario
        stmt = select(
            Project.project_id,
        ).where(
            Project.project_id == project_user.project_id,
            project_user.user_id == user_id,
        )

        project_ids = session.exec(stmt).all()

        # Guarda la metadata de la conexión
        metadata = {
            "connection_id": connection_id,
            "user_id": user_id,
            "project_ids": project_ids,
        }

        await self.redis.set(f"connection:{connection_id}", json.dumps(metadata))
        await self.redis.sadd(f"user_connections:{user_id}", connection_id)

        for project_id in project_ids:
            await self.redis.sadd(f"project_connections:{project_id}", connection_id)

        # Suscribe al usuario a todos los canales de sus proyectos
        await self._subscribe(websocket, user_id, project_ids, connection_id)

        return connection_id


manager = RedisConnectionManager(redis_client)


async def send_pending_notifications(user_id: int):
    session = sessionlocal
    pending = get_pending_notifications_for_user(user_id)
    if not pending:
        return {"detail": "No habian notificaciones a enviar"}
    else:
        for n in pending:
            notification_to_send = format_notification(
                notification_type=n.type, message=n.payload
            )
            await manager.send_to_user(user_id=user_id, message=notification_to_send)
            n.status = Notify_State.ENVIADO
        session.commit()
        logger.info(f"[send_pending_notifications] Notifications were updated")
