from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict
from datetime import datetime
import json
from models import schemas

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

manager = ConnectionManager()

@router.websocket("/ws/{project_id}/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int, project_id: int):
    await manager.connect(websocket, project_id)
    
    msg_connect = schemas.Message(user_id=client_id,
                                  project_id=project_id,
                                  timestamp=datetime.now(),
                                  content=f'El usuario {client_id} se ha conectado al projecto {project_id}')
    
    await manager.broadcast(msg_connect.model_dump_json(), project_id)
    
    try:
        while True:
            data = await websocket.receive_text()

            msg = schemas.Message(content=data,
                                user_id=client_id,
                                project_id=project_id,
                                timestamp=datetime.now())
            
            await manager.broadcast(msg.model_dump_json(), project_id)

    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
        
        msg_disconnect = schemas.Message(user_id=client_id,
                                         project_id=project_id,
                                         timestamp=datetime.now(),
                                         content=f'El usuario {client_id} se ha desconectado del projecto {project_id}')
        
        await manager.broadcast(msg_disconnect.model_dump_json(), project_id)