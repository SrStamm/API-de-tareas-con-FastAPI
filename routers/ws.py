from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, WebSocketException
from typing import List, Dict
from datetime import datetime
from models import schemas, db_models, exceptions
from db.database import get_session, Session, select, SQLAlchemyError
from .auth import auth_user_ws, auth_user

router = APIRouter()

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
            for connection in self.active_connections[project_id]:
                try:
                    await connection.send_text(message)
                except Exception:
                    self.active_connections[project_id].remove(connection)

async def get_current_user_ws(session: Session, websocket: WebSocket):
    try:
        auth_header = websocket.headers.get("Authorization")
        print(f"Header Authorization recibido: {auth_header}")
        if not auth_header:
            print("Falta header Authorization")
            await websocket.close(code=1008)
            raise WebSocketException(code=1008)
        
        if not auth_header.startswith("Bearer "):
            print(f"Formato de Authorization inválido: {auth_header}")
            await websocket.close(code=1008)
            raise WebSocketException(code=1008)
        
        token = auth_header.replace("Bearer ", "")
        print(f"Token extraído: {token}")
        user = await auth_user_ws(token, session)
        if not user:
            print(f"Usuario no encontrado para token: {token}")
            await websocket.close(code=1008)
            raise WebSocketException(code=1008)
        print(f"Usuario autenticado: user_id={user.user_id}, username={user.username}")
        return user
    except Exception as e:
        print(f"Error en get_current_user_ws: {str(e)}")
        await websocket.close(code=1008, reason=f"Error de autenticación: {str(e)}")
        raise

def verify_user_in_project(user_id: int, project_id: int, session: Session = Depends(get_session)):
    print(f"Verificando usuario {user_id} en proyecto {project_id}")
    project = session.get(db_models.Project, project_id)
    if not project:
        print(f"Proyecto {project_id} no encontrado")
        raise exceptions.ProjectNotFoundError(project_id)
    
    stmt = select(db_models.project_user).where(
        db_models.project_user.user_id == user_id,
        db_models.project_user.project_id == project_id
    )
    project_user = session.exec(stmt).first()
    if not project_user:
        print(f"Usuario {user_id} no autorizado para proyecto {project_id}")
        raise exceptions.NotAuthorized(user_id)
    print(f"Usuario {user_id} verificado en proyecto {project_id}")
    return project_user

manager = ConnectionManager()

@router.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: int, session: Session = Depends(get_session)):
    user = await get_current_user_ws(session, websocket)
    print(f"Iniciando conexión WebSocket para project_id={project_id}, user_id={user.user_id}")
    try:
        verify_user_in_project(user_id=user.user_id, project_id=project_id, session=session)

    except exceptions.ProjectNotFoundError as e:
        print(f"Error: Proyecto {project_id} no encontrado - {str(e)}")
        await websocket.close(code=1008, reason=f"Proyecto {project_id} no encontrado")
        return
    
    except exceptions.NotAuthorized as e:
        print(f"Error: Usuario {user.user_id} no autorizado para proyecto {project_id} - {str(e)}")
        await websocket.close(code=1008, reason=f"Usuario no autorizado para proyecto {project_id}")
        return
    
    except Exception as e:
        print(f"Error inesperado en WebSocket: {str(e)}")
        await websocket.close(code=1008, reason=f"Error interno: {str(e)}")
        return

    print(f"Conexión establecida para usuario {user.user_id} en proyecto {project_id}")
    await manager.connect(websocket, project_id)
    
    msg_connect = schemas.Message(
        user_id=user.user_id,
        project_id=project_id,
        timestamp=datetime.now(),
        content=f'El usuario {user.user_id} se ha conectado al projecto {project_id}'
    )
    
    await manager.broadcast(msg_connect.model_dump_json(), project_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = schemas.Message(
                content=data,
                user_id=user.user_id,
                project_id=project_id,
                timestamp=datetime.now()
            )
            
            message = db_models.ProjectChat(
                project_id=project_id,
                user_id=user.user_id,
                message=data
            )
            
            session.add(message)
            session.commit()            
            await manager.broadcast(msg.model_dump_json(), project_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
        msg_disconnect = schemas.Message(
            user_id=user.user_id,
            project_id=project_id,
            timestamp=datetime.now(),
            content=f'El usuario {user.user_id} se ha desconectado del projecto {project_id}'
        )
        await manager.broadcast(msg_disconnect.model_dump_json(), project_id)

@router.get('/chat/{project_id}')
def get_chat(project_id: int,
            user: db_models.User = Depends(auth_user),
            session: Session = Depends(get_session)):
    try:
        stmt = (select(db_models.ProjectChat).where(
            db_models.ProjectChat.project_id == project_id,
            db_models.ProjectChat.user_id == user.user_id
        ))

        messages_chat = session.exec(stmt).all()

        if not messages_chat:
            raise exceptions.ChatNotFoundError(project_id)
        
        return messages_chat
    
    except SQLAlchemyError as e:
        raise exceptions.DatabaseError(error=e, func='get_chat')