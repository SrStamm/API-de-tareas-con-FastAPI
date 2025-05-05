import pytest, json
from conftest import auth_headers, client, test_create_project_init, select, db_models
from sqlalchemy.exc import SQLAlchemyError
from routers import ws
from models import exceptions

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
            
    except ws.WebSocketDisconnect as e:
        print(f"WebSocketDisconnect: code={e.code}, reason={e.reason}")
        raise

def test_get_chat(client, auth_headers):
    response = client.get('/chat/1', headers=auth_headers)
    assert response.status_code == 200
    messages = response.json()
    assert isinstance(messages, list)
    for message in messages:
        assert all(key in message for key in ['chat_id', 'project_id', 'user_id', 'message', 'timestamp'])

def test_get_chat_error(mocker):
    session_mock = mocker.Mock()
    mock_user = mocker.Mock(spec=db_models.User)

    # Excepcion chat no encontrado
    session_mock.exec.return_value.all.return_value = []

    with pytest.raises(exceptions.ChatNotFoundError):
        ws.get_chat(
                project_id=1,
                user=mock_user,
                session=session_mock)
    
    # Prueba la excepcion de DB
    session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        ws.get_chat(
                project_id=1,
                user=mock_user,
                session=session_mock)

def test_verify_user_in_project_error(mocker):
    session_mock = mocker.Mock()
    
    # Excepcion usuario no autorizado
    session_mock.exec.return_value.first.return_value = []

    with pytest.raises(exceptions.NotAuthorized):
        ws.verify_user_in_project(
                    user_id=1,
                    project_id=1,
                    session=session_mock)
    
    # Excepcion project no encontrado
    session_mock.get.return_value = []

    with pytest.raises(exceptions.ProjectNotFoundError):
        ws.verify_user_in_project(
                    user_id=1,
                    project_id=1,
                    session=session_mock)