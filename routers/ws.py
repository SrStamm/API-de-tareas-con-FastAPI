from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict
router = APIRouter()

class ConnectionManager:
    # Crea una lista de conexiones activas
    def __init__(self):
        self.active_conecctions: Dict[int, List[WebSocket]] = {}

    # Conecta el usuario a ws y lo agrega a la lista de conexiones activas
    async def connect(self, websocket: WebSocket, project_id: int):
        await websocket.accept()
        if project_id not in self.active_conecctions:
            self.active_conecctions[project_id] = []
        self.active_conecctions[project_id].append(websocket)

    # Desconecta y elimina el usuario de conexiones
    def disconnect(self, websocket: WebSocket, project_id: int):
        if project_id in self.active_conecctions:
            self.active_conecctions[project_id].remove(websocket)

    # Envia un mensaje personal
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, project_id: int):
        if project_id in self.active_conecctions:
            for connection in self.active_conecctions[project_id]:
                await connection.send_text(message)

manager = ConnectionManager()

@router.websocket("/ws/{project_id}/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int, project_id: int):
    await manager.connect(websocket, project_id)
    try:
        while True:
            data = await websocket.receive_text()
            # await manager.send_personal_message(f"You wrote: {data}", websocket)
            await manager.broadcast(f"Mensaje en proyecto {project_id} de user {client_id}: {data}", project_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
        await manager.broadcast(f"Client #{client_id} left the chat", project_id)