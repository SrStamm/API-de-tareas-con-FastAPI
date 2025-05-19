from typing import Dict, List
from fastapi import WebSocket
from .logger import logger

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

manager = ConnectionManager()