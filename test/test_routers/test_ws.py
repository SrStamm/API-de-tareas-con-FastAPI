import pytest
from conftest import auth_headers, client, test_create_project_init, test_user, select, db_models
import json
from routers.ws import WebSocketDisconnect

def test_websocket_connection(client, auth_headers, test_create_project_init, test_session):
    print("Iniciando test_websocket_connection")
    print("Token usado:", auth_headers["Authorization"])
    
    # Verificar proyecto y asociación
    project = test_session.get(db_models.Project, 1)
    print(f"Proyecto 1 existe: {project is not None}")
    if project:
        stmt = select(db_models.project_user).where(
            db_models.project_user.user_id == 1,
            db_models.project_user.project_id == 1
        )
        project_user = test_session.exec(stmt).first()
        print(f"Usuario 1 en proyecto 1: {project_user is not None}")
    
    try:
        # Usar solo el header Authorization
        headers = {"Authorization": auth_headers["Authorization"]}
        with client.websocket_connect("/ws/1", headers=headers) as ws:
            print("Conexión WebSocket establecida")
            
            # Recibir el mensaje de conexión
            connect_msg = json.loads(ws.receive_text())
            print(f"Mensaje de conexión recibido: {connect_msg}")
            assert "se ha conectado" in connect_msg["content"]
            
            # Enviar un mensaje
            ws.send_text("Hola")
            
            # Recibir el mensaje transmitido
            received_msg = json.loads(ws.receive_text())
            print(f"Mensaje recibido: {received_msg}")
            assert received_msg["content"] == "Hola"
            assert received_msg["user_id"] == 1  # Verifica el user_id
            assert received_msg["project_id"] == 1  # Verifica el project_id
            
            # Verificar que el mensaje se guardó en la base de datos
            stmt = select(db_models.ProjectChat).where(
                db_models.ProjectChat.project_id == 1,
                db_models.ProjectChat.user_id == 1,
                db_models.ProjectChat.message == "Hola"
            )
            chat_message = test_session.exec(stmt).first()
            assert chat_message is not None, "El mensaje no se guardó en la base de datos"
            
    except WebSocketDisconnect as e:
        print(f"WebSocketDisconnect: code={e.code}, reason={e.reason}")
        raise