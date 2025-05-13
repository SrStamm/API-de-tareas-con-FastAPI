from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, WebSocketException, Request
from typing import List, Dict
from datetime import datetime
from models import schemas, db_models, exceptions, responses
from db.database import get_session, Session, select, SQLAlchemyError
from .auth import auth_user_ws, auth_user
from core.logger import logger
from core.limiter import limiter
import json

router = APIRouter(tags=['WebSocket'])

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

async def get_current_user_ws(session: Session, websocket: WebSocket):
    try:
        auth_header = websocket.headers.get("Authorization")
        
        if not auth_header:
            logger.info(f'Error: No tiene el Header')
            await websocket.close(code=1008, reason='Error de autenticacion')
            raise WebSocketException(code=1008)
        
        if not auth_header.startswith("Bearer "):
            logger.info('Error: Formato incorrecto')
            await websocket.close(code=1008, reason='Formato de token invalido')
            raise WebSocketException(code=1008)
        
        token = auth_header.replace("Bearer ", "")
        user = await auth_user_ws(token, session)

        if not user:
            logger.info('Error: Usuario no encontrado')
            await websocket.close(code=1008, reason=f'User no encontrado para token')
            raise WebSocketException(code=1008)
        
        return user

    except WebSocketException as e:
        logger.warning(f'Error: Desconeccion repentina: {e}')
        raise

    except Exception as e:
        logger.warning(f'Error: Desconeccion repentina: {e}')
        await websocket.close(code=1008, reason=f"Error de autenticación: {str(e)}")
        raise

def verify_user_in_project(user_id: int, project_id: int, session: Session = Depends(get_session)):
    print(f"Verificando usuario {user_id} en proyecto {project_id}")
    logger.info(f"Verificando usuario {user_id} en proyecto {project_id}")
    project = session.get(db_models.Project, project_id)
    if not project:
        logger.info(f"Proyecto {project_id} no encontrado")
        print(f"Proyecto {project_id} no encontrado")
        raise exceptions.ProjectNotFoundError(project_id)
    
    stmt = select(db_models.project_user).where(
        db_models.project_user.user_id == user_id,
        db_models.project_user.project_id == project_id
    )
    project_user = session.exec(stmt).first()
    if not project_user:
        logger.info(f"Usuario {user_id} no autorizado para proyecto {project_id}")
        print(f"Usuario {user_id} no autorizado para proyecto {project_id}")
        raise exceptions.NotAuthorized(user_id)
    print(f"Usuario {user_id} verificado en proyecto {project_id}")
    logger.info(f"Usuario {user_id} verificado en proyecto {project_id}")
    return project_user

manager = ConnectionManager()

@router.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: int, session: Session = Depends(get_session)):
    # Obtiene el usuario actual
    user = await get_current_user_ws(session, websocket)
    
    try:
        # Verifica que el usuario exista en el proyecto
        verify_user_in_project(user_id=user.user_id, project_id=project_id, session=session)

    except exceptions.ProjectNotFoundError as e:
        await websocket.close(code=1008, reason=f"Proyecto {project_id} no encontrado")
        return
    
    except exceptions.NotAuthorized as e:
        await websocket.close(code=1008, reason=f"Usuario no autorizado para proyecto {project_id}")
        return
    
    except Exception as e:
        await websocket.close(code=1008, reason=f"Error interno: {str(e)}")
        return

    # Conecta el usario a websocket
    await manager.connect(websocket=websocket, project_id=project_id, user_id=user.user_id)
    
    msg_connect = schemas.Message(
        user_id=user.user_id,
        project_id=project_id,
        timestamp=datetime.now(),
        content=f'El usuario {user.user_id} se ha conectado al projecto {project_id}'
    )

    outgoing_event = schemas.WebSocketEvent(
        type='user_connected',
        payload=msg_connect.model_dump()
    )

    outgoing_event_json = outgoing_event.model_dump_json()

    await manager.broadcast(outgoing_event_json, project_id)

    try:
        while True:
            # Obtiene la data en json
            data_json = await websocket.receive_json()

            try:
                # Verifica que el evento tenga estructura general de evento
                event = schemas.WebSocketEvent(**data_json)

                if event.type == 'group_message':
                    # Verifica que tenga los datos del schema
                    message_payload = schemas.GroupMessagePayload(**event.payload)

                    # Crea el mensaje a guardar en BD
                    message = db_models.ProjectChat(
                        project_id=project_id,
                        user_id=user.user_id,
                        message=message_payload.content
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
                        timestamp=message.timestamp
                    )

                    # Crea el evento completo
                    outgoing_event = schemas.WebSocketEvent(
                        type='group_message',
                        payload=outgoing_payload.model_dump()
                    )

                    # Parsea a json
                    outgoing_event_json = outgoing_event.model_dump_json()

                    # Envia al broadcast
                    await manager.broadcast(outgoing_event_json, project_id)
                    logger.info(f'Broadcast group message ID {message.chat_id} for project {project_id}')

                if event.type == 'personal_message':
                    # Verifica que tenga los datos del schema
                    message_payload = schemas.PersonalMessagePayload(**event.payload)

                    # Crea el mensaje de salida, que se envia al usuario
                    outgoing_payload = schemas.OutgoingPersonalMessagePayload(
                        sender_id=user.user_id,
                        received_user_id=message_payload.received_user_id,
                        content=message_payload.content,
                        timestamp=datetime.now()
                    )

                    # Crea el evento completo
                    outgoing_event = schemas.WebSocketEvent(
                        type='personal_message',
                        payload=outgoing_payload.model_dump()
                    )

                    # Parsea a json
                    outgoing_event_json = outgoing_event.model_dump_json()

                    # Envia al usuario
                    await manager.send_to_user(outgoing_event_json, message_payload.received_user_id)
                    logger.info(f'Personal message send for user with user_id {user.user_id} to user with user_id {message_payload.received_user_id}')
    
                elif event.type == 'notification':
                    # Verifica que tenga los datos del schema
                    notification_payload = schemas.NotificationPayload(**event.payload)

                    # Crea la notifiacion de salida
                    outgoing_payload = schemas.OutgoingNotificationPayload(
                        notification_type=notification_payload.notification_type,
                        message=notification_payload.message,
                        related_entity_id=notification_payload.related_entity_id,
                        timestamp= datetime.now()
                    )

                    # Crea el evento completo
                    outgoing_event = schemas.WebSocketEvent(
                        type='notification',
                        payload=outgoing_payload.model_dump()
                    )

                    # Parsea a json
                    outgoing_event_json = outgoing_event.model_dump_json()

                    # Envia la notificacion
                    await manager.broadcast(outgoing_event_json, project_id)
                    logger.info(f'Broadcast notification for project {project_id}')

                else:
                    # Manejar tipos de eventos desconocidos
                    logger.warning(f'Received unknown event type: {event.type} from user {user.user_id} in project {project_id}')

            except json.JSONDecodeError:
                # Error si el mensaje no es un JSON válido
                logger.error(f"Received invalid JSON from user {user.user_id} in project {project_id}")
                await websocket.send_json({"type": "error", "payload": {"message": "Invalid JSON format."}})

            except ValueError as ve: # Captura errores de validación
                logger.error(f"Payload validation error for event type {event.type}: {ve} from user {user.user_id} in project {project_id}")
                await websocket.send_json({"type": "error", "payload": {"message": f"Invalid payload for type {event.type}."}})

            except Exception as e:
                # Captura cualquier otro error durante el procesamiento del mensaje
                logger.error(f"Error processing message from user {user.user_id} in project {project_id}: {e}", exc_info=True)
                await websocket.send_json({"type": "error", "payload": {"message": "Internal server error processing message."}})

    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id, user.user_id)
        logger.info(f'El usuario con ID {user.user_id} se desconecto')

        msg_disconnect = schemas.Message(
            user_id=user.user_id,
            project_id=project_id,
            timestamp=datetime.now(),
            content=f'El usuario {user.user_id} se ha desconectado del projecto {project_id}'
        )
        await manager.broadcast(msg_disconnect.model_dump_json(), project_id)
    
    except RuntimeError as e:
        logger.error(f'Error de ejecución: {e}')
        manager.disconnect(websocket, project_id, user.user_id)
    
    except ValueError:
        logger.error(f'Se esperaba un mensaje de texto valido')
        manager.disconnect(websocket, project_id, user.user_id)

    except SQLAlchemyError as e:
        logger.error(f'Error interno en WebSocket: {e}')
        manager.disconnect(websocket, project_id, user.user_id)
    
    except Exception as e:
        logger.error(f'Error inesperado: {e}')
        manager.disconnect(websocket, project_id, user.user_id)

@router.get('/chat/{project_id}',
        description=""" Obtiene el chat de un proyecto.
                        'skip' recibe un int que saltea el resultado obtenido.
                        'limit' recibe un int para limitar los resultados obtenidos.""",
        responses={
            200:{'description':'Chat del proyecto obtenido', 'model':schemas.ChatMessage},
            500:{'description':'Error interno', 'model':responses.DatabaseErrorResponse}
        })
@limiter.limit("20/minute")
def get_chat(request: Request,
            project_id: int,
            limit:int = 100,
            skip: int = 0,
            user: db_models.User = Depends(auth_user),
            session: Session = Depends(get_session)) -> List[schemas.ChatMessage]:

    try:
        stmt = (select(db_models.ProjectChat)
                .where( db_models.ProjectChat.project_id == project_id,
                        db_models.ProjectChat.user_id == user.user_id)
                .limit(limit).offset(skip))

        messages_chat = session.exec(stmt).all()

        if not messages_chat:
            raise exceptions.ChatNotFoundError(project_id)
        
        return messages_chat
    
    except SQLAlchemyError as e:
        raise exceptions.DatabaseError(error=e, func='get_chat')