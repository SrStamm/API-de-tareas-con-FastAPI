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
    
    # Conectar al WebSocket con solo el header Authorization
    with client.websocket_connect("/ws/1", headers={"Authorization": auth_headers["Authorization"]}) as ws:
        print("Conexión WebSocket establecida")