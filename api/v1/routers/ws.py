from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    WebSocketException,
    Request,
)
from typing import List
from datetime import datetime
from models import schemas, db_models, exceptions, responses
from db.database import get_session, Session, select, SQLAlchemyError
from .auth import auth_user_ws
from dependency.auth_dependencies import get_current_user
from core.logger import logger
from core.limiter import limiter
from core.socket_manager import manager, send_pending_notifications
from core.event_ws import format_personal_message
from core.utils import found_user_in_project_or_404
import json

router = APIRouter(tags=["WebSocket"])


async def get_current_user_ws(session: Session, websocket: WebSocket):
    try:
        auth_header = websocket.headers.get("Authorization")
        token = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
        else:
            token = websocket.query_params.get("token")

        if not token:
            logger.error("[get_current_user_ws] Not found Error: User not found")
            await websocket.close(code=1008, reason="User not found for token")
            raise WebSocketException(code=1008)

        user = await auth_user_ws(token, session)

        if not user:
            logger.info("[get_current_user_ws] Not found Error: User not found")
            await websocket.close(code=1008, reason="User not found for token")
            raise WebSocketException(code=1008)

        return user

    except WebSocketException as e:
        logger.warning(
            f"[get_current_user_ws] WebScoket Exception Error | Sudden disconnection: {str(e)}"
        )
        raise

    except Exception as e:
        logger.warning(
            f"[get_current_user_ws] Exception Error | Sudden disconnection: {str(e)}"
        )
        await websocket.close(code=1008, reason=f"Authentication error: {str(e)}")
        raise


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session: Session = Depends(get_session),
):
    # Obtiene el usuario actual
    user = await get_current_user_ws(session, websocket)

    logger.info("Usuario conectado")

    try:
        # Conecta a todos los proyectos
        conn_id = await manager.connect_to_user_projects(
            websocket=websocket, user_id=user.user_id, session=session
        )

    except Exception as e:
        await websocket.close(code=1008, reason=f"Internal error: {str(e)}")
        return

    connection_event = format_personal_message(
        user_id=user.user_id, message=f"User {user.user_id} connected"
    )

    await manager.send_to_user(message=connection_event, user_id=user.user_id)

    await send_pending_notifications(user.user_id)

    try:
        while True:
            # Obtiene la data en json
            data_json = await websocket.receive_json()

            try:
                # Verifica que el evento tenga estructura general de evento
                event = schemas.WebSocketEvent(**data_json)

                event_type = event.type.strip()

                if event_type == "group_message":
                    # Verifica que tenga los datos del schema
                    message_payload = schemas.GroupMessagePayload(**event.payload)

                    # Crea el mensaje a guardar en BD
                    message = db_models.ProjectChat(
                        project_id=message_payload.project_id,
                        user_id=user.user_id,
                        message=message_payload.content,
                    )

                    session.add(message)
                    session.commit()
                    session.refresh(message)

                    # Crea el mensaje de salida, que se envia al grupo
                    outgoing_payload = schemas.OutgoingGroupMessagePayload(
                        id=message.chat_id,
                        project_id=message.project_id,
                        sender_id=message.user_id,
                        content=message.message,
                        timestamp=message.timestamp,
                    )

                    # Crea el evento completo
                    outgoing_event = schemas.WebSocketEvent(
                        type="group_message", payload=outgoing_payload.model_dump()
                    )

                    # Parsea a json
                    outgoing_event_json = outgoing_event.model_dump_json()

                    # Envia al broadcast
                    await manager.broadcast(outgoing_event_json, message.project_id)
                    logger.info(
                        f"Broadcast group message ID {message.chat_id} for project {message.project_id} via WS"
                    )

                if event_type == "personal_message":
                    # Verifica que tenga los datos del schema
                    message_payload = schemas.PersonalMessagePayload(**event.payload)

                    # Crea el mensaje de salida, que se envia al usuario
                    outgoing_payload = schemas.OutgoingPersonalMessagePayload(
                        sender_id=user.user_id,
                        received_user_id=message_payload.received_user_id,
                        content=message_payload.content,
                        timestamp=datetime.now(),
                    )

                    # Crea el evento completo
                    outgoing_event = schemas.WebSocketEvent(
                        type="personal_message", payload=outgoing_payload.model_dump()
                    )

                    # Parsea a json
                    outgoing_event_json = outgoing_event.model_dump_json()

                    # Envia al usuario
                    await manager.send_to_user(
                        outgoing_event_json, message_payload.received_user_id
                    )
                    logger.info(
                        f"Personal message send for user with user_id {user.user_id} to user with user_id {message_payload.received_user_id}"
                    )

                elif event_type == "notification":
                    # Verifica que tenga los datos del schema
                    notification_payload = schemas.NotificationPayload(**event.payload)

                    # Crea la notifiacion de salida
                    outgoing_payload = schemas.OutgoingNotificationPayload(
                        notification_type=notification_payload.notification_type,
                        message=notification_payload.message,
                        related_entity_id=notification_payload.related_entity_id,
                        timestamp=datetime.now(),
                    )

                    # Crea el evento completo
                    outgoing_event = schemas.WebSocketEvent(
                        type="notification", payload=outgoing_payload.model_dump()
                    )

                    # Parsea a json
                    outgoing_event_json = outgoing_event.model_dump_json()

                    # Envia la notificacion
                    await manager.send_to_user(outgoing_event_json, user.user_id)
                    logger.info(f"Notification sent to user {user.user_id} for project")

                else:
                    # Manejar tipos de eventos desconocidos
                    logger.warning(
                        f"Received unknown event type: {event_type} from user {user.user_id} in project",
                    )
                    logger.info(f"Evento: {event}")

            except json.JSONDecodeError:
                # Error si el mensaje no es un JSON válido
                logger.error(
                    f"Received invalid JSON from user {user.user_id} in project"
                )
                await websocket.send_json(
                    {"type": "error", "payload": {"message": "Invalid JSON format."}}
                )

            except ValueError as ve:  # Captura errores de validación
                event_type = (
                    data_json.get("type") if "data_json" in locals() else "unknown"
                )
                logger.error(
                    f"Payload validation error for event type {event_type}: {ve} from user {user.user_id} in project"
                )
                await websocket.send_json(
                    {
                        "type": "error",
                        "payload": {
                            "message": f"Invalid payload for type {event_type}."
                        },
                    }
                )

            except Exception as e:
                # Captura cualquier otro error durante el procesamiento del mensaje
                logger.error(
                    f"Error processing message from user {user.user_id} in project: {e}",
                    exc_info=True,
                )
                await websocket.send_json(
                    {
                        "type": "error",
                        "payload": {
                            "message": "Internal server error processing message."
                        },
                    }
                )

    except WebSocketDisconnect:
        await manager.disconnect(conn_id)  # Usa await para asegurar que se ejecute
        logger.info(f"El usuario con ID {user.user_id} se desconecto")

    except RuntimeError as e:
        logger.error(f"Error de ejecución: {e}")
        await manager.disconnect(conn_id)

    except ValueError as e:
        logger.error(f"Se esperaba un mensaje de texto valido: {e}")
        await manager.disconnect(conn_id)

    except SQLAlchemyError as e:
        logger.error(f"Error interno en WebSocket: {e}")
        await manager.disconnect(conn_id)

    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        await manager.disconnect(conn_id)


@router.get(
    "/chat/{project_id}",
    description=""" Obtiene el chat de un proyecto.
                        'skip' recibe un int que saltea el resultado obtenido.
                        'limit' recibe un int para limitar los resultados obtenidos.""",
    responses={
        200: {
            "description": "Chat del proyecto obtenido",
            "model": schemas.ChatMessage,
        },
        500: {"description": "Error interno", "model": responses.DatabaseErrorResponse},
    },
)
@limiter.limit("20/minute")
def get_chat(
    request: Request,
    project_id: int,
    limit: int = 100,
    skip: int = 0,
    user: db_models.User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> List[schemas.ChatMessage]:
    try:
        stmt = (
            select(db_models.ProjectChat)
            .where(
                db_models.ProjectChat.project_id == project_id,
            )
            .limit(limit)
            .offset(skip)
        )

        response = session.exec(stmt)
        messages_chat = response.all()

        if not messages_chat:
            raise exceptions.ChatNotFoundError(project_id)

        return messages_chat

    except SQLAlchemyError as e:
        raise exceptions.DatabaseError(error=e, func="get_chat")


@router.post("/chat/{project_id}")
async def send_message_to_project(
    project_id: int,
    message_payload: schemas.GroupMessagePayload,
    user: db_models.User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        found_user_in_project_or_404(user.user_id, project_id, session)

        # Crea el mensaje a guardar en BD
        message = db_models.ProjectChat(
            project_id=project_id, user_id=user.user_id, message=message_payload.content
        )

        session.add(message)
        session.commit()
        session.refresh(message)

        # Crea el mensaje de salida, que se envia al grupo
        outgoing_payload = schemas.OutgoingGroupMessagePayload(
            id=message.chat_id,
            project_id=message.project_id,
            sender_id=message.user_id,
            content=message.message,
            timestamp=message.timestamp,
        )

        # Crea el evento completo
        outgoing_event = schemas.WebSocketEvent(
            type="group_message", payload=outgoing_payload.model_dump()
        )

        # Parsea a json
        outgoing_event_json = outgoing_event.model_dump_json()

        # Envia al broadcast
        await manager.broadcast(outgoing_event_json, project_id)

        return {
            "detail": f"Mensaje enviado con exito al proyecto {project_id} por user {user.user_id}"
        }

    except SQLAlchemyError as e:
        session.rollback()
        raise exceptions.DatabaseError(error=e, func="send_message_to_project")
