import pytest, json
from conftest import auth_headers, client, test_create_group_init, test_create_project_init, test_user
from models import schemas
from datetime import datetime

@pytest.mark.asyncio
async def test_websocket_connection(client, auth_headers, test_create_project_init):
    # Conectar al WebSocket
    with client.websocket_connect(f"/ws/1", headers=auth_headers) as ws:
        # 1. Recibir mensaje de conexión
        connect_msg = json.loads(await ws.receive_text())
        assert connect_msg["content"] == f"El usuario {test_user.user_id} se ha conectado al projecto 1"
        
        # 2. Enviar mensaje
        test_msg = "Hola desde el test"
        await ws.send_text(test_msg)
        
        # 3. Recibir broadcast del mensaje enviado
        received_msg = json.loads(await ws.receive_text())
        assert received_msg["content"] == test_msg
        assert received_msg["user_id"] == test_user.user_id
        
        # 4. Verificar desconexión
        await ws.close()
        disconnect_msg = json.loads(await ws.receive_text())
        assert disconnect_msg["content"] == f"El usuario {test_user.user_id} se ha desconectado del projecto 1"