import pytest, json
from conftest import auth_headers, client, test_create_project_init, select, db_models
from sqlalchemy.exc import SQLAlchemyError
from fastapi import WebSocketException, WebSocket
from routers import ws
from models import exceptions
from unittest.mock import AsyncMock
from starlette.requests import Request

def test_websocket_connection(client, auth_headers, test_create_project_init, test_session):
    g = test_create_project_init
    
    try:
        # Usar solo el header Authorization
        headers = {"Authorization": auth_headers["Authorization"]}
        with client.websocket_connect("/ws/1", headers=headers) as ws:

            # Recibir el mensaje de conexión
            connect_msg = json.loads(ws.receive_text())
            assert "se ha conectado" in connect_msg["content"]
            
            # Enviar un mensaje
            ws.send_text("Hola")
            
            # Recibir el mensaje transmitido
            received_msg = json.loads(ws.receive_text())
            
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

def test_get_chat(client, auth_headers, test_create_project_init):
    g = test_create_project_init

    response = client.get('/chat/1', headers=auth_headers)
    assert response.status_code == 200
    messages = response.json()
    assert isinstance(messages, list)
    for message in messages:
        assert all(key in message for key in ['chat_id', 'project_id', 'user_id', 'message', 'timestamp']) 

def test_get_chat_error(mocker):
    session_mock = mocker.Mock()
    mock_user = mocker.Mock(spec=db_models.User)
    mock_request = mocker.Mock(spec=Request)

    # Excepcion chat no encontrado
    session_mock.exec.return_value.all.return_value = []

    with pytest.raises(exceptions.ChatNotFoundError):
        ws.get_chat(
                request=mock_request,
                project_id=1,
                user=mock_user,
                session=session_mock)
    
    # Prueba la excepcion de DB
    session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        ws.get_chat(
                request=mock_request,
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

@pytest.mark.asyncio
async def test_get_current_user_ws_header_error(mocker):
    session_mock = mocker.Mock()

    ws_mock = mocker.Mock(spec=WebSocket)
    ws_mock.headers = {}
    ws_mock.close = AsyncMock()
    
    with pytest.raises(WebSocketException):
        await ws.get_current_user_ws( session=session_mock, websocket=ws_mock)

    ws_mock.close.assert_awaited_once_with(code=1008, reason='Error de autenticacion')

@pytest.mark.asyncio
async def test_get_current_user_ws_format_error(mocker):
    session_mock = mocker.Mock()

    ws_mock = mocker.Mock(spec=WebSocket)
    ws_mock.headers = {'Authorization':'hola'}
    ws_mock.close = AsyncMock()
    
    with pytest.raises(WebSocketException):
        await ws.get_current_user_ws( session=session_mock, websocket=ws_mock)

    ws_mock.close.assert_awaited_once_with(code=1008, reason='Formato de token invalido')

@pytest.mark.asyncio
async def test_get_current_user_ws_user_not_found_error(mocker):
    session_mock = mocker.Mock()

    ws_mock = mocker.Mock(spec=WebSocket)
    ws_mock.headers = {'Authorization':'Bearer '}
    ws_mock.close = AsyncMock()
    
    with pytest.raises(WebSocketException):
        await ws.get_current_user_ws( session=session_mock, websocket=ws_mock)

    ws_mock.close.assert_awaited_once_with(code=1008, reason='User no encontrado para token')

@pytest.mark.asyncio
async def test_websocket_endpoint_not_found_project_error(mocker):
    # Session
    session_mock = mocker.Mock()

    # WebSocket simulado
    ws_mock = mocker.Mock(spec=WebSocket)
    ws_mock.headers = {'Authorization':'Bearer token'}
    ws_mock.close = AsyncMock()
    
    # Usuario simulado
    mock_user = mocker.Mock()
    mock_user.user_id = 1
    mocker.patch('routers.ws.get_current_user_ws', return_value=mock_user)

    # Forzar que verify_user_in_project lance la excepción
    mocker.patch('routers.ws.verify_user_in_project', side_effect=exceptions.ProjectNotFoundError(project_id=999))

    # Ejecutar el endpoint
    await ws.websocket_endpoint(websocket=ws_mock, project_id=999, session=session_mock)

    # Verificar que se cerró con el mensaje correcto
    ws_mock.close.assert_awaited_once_with(code=1008, reason="Proyecto 999 no encontrado")

@pytest.mark.asyncio
async def test_websocket_endpoint_not_authorized_error(mocker):
    # Session
    session_mock = mocker.Mock()

    # WebSocket simulado
    ws_mock = mocker.Mock(spec=WebSocket)
    ws_mock.headers = {'Authorization':'Bearer token'}
    ws_mock.close = AsyncMock()
    
    # Usuario simulado
    mock_user = mocker.Mock()
    mock_user.user_id = 1
    mocker.patch('routers.ws.get_current_user_ws', return_value=mock_user)

    # Forzar que verify_user_in_project lance la excepción
    mocker.patch('routers.ws.verify_user_in_project', side_effect=exceptions.NotAuthorized(user_id=1))

    # Ejecutar el endpoint
    await ws.websocket_endpoint(websocket=ws_mock, project_id=999, session=session_mock)

    # Verificar que se cerró con el mensaje correcto
    ws_mock.close.assert_awaited_once_with(code=1008, reason="Usuario no autorizado para proyecto 999")