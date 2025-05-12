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
        self.active_connections: Dict[int, List[WebSocket]] = {}

    # Conecta el usuario a ws y lo agrega a la lista de conexiones activas
    async def connect(self, websocket: WebSocket, project_id: int):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)

    # Desconecta y elimina el usuario de conexiones
    def disconnect(self, websocket: WebSocket, project_id: int):
        if project_id in self.active_connections:
            self.active_connections[project_id].remove(websocket)

    # Envia un mensaje personal
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, project_id: int):
        if project_id in self.active_connections:
            for connection in list(self.active_connections[project_id]):
                try:
                    await connection.send_text(message)
                except Exception:
                    self.active_connections[project_id].remove(connection)

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
    user = await get_current_user_ws(session, websocket)
    
    try:
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

    await manager.connect(websocket, project_id)
    
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

                    await manager.broadcast(outgoing_event_json, project_id)
                    logger.info(f'Broadcast group message ID {message.chat_id} for project {project_id}')

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
        manager.disconnect(websocket, project_id)

        msg_disconnect = schemas.Message(
            user_id=user.user_id,
            project_id=project_id,
            timestamp=datetime.now(),
            content=f'El usuario {user.user_id} se ha desconectado del projecto {project_id}'
        )
        await manager.broadcast(msg_disconnect.model_dump_json(), project_id)
    
    except RuntimeError as e:
        logger.error(f'Error de ejecución: {e}')
        manager.disconnect(websocket, project_id)
    
    except ValueError:
        logger.error(f'Se esperaba un mensaje de texto valido')
        manager.disconnect(websocket, project_id)

    except SQLAlchemyError as e:
        logger.error(f'Error interno en WebSocket: {e}')
        manager.disconnect(websocket, project_id)
    
    except Exception as e:
        logger.error(f'Error inesperado: {e}')
        manager.disconnect(websocket, project_id)

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