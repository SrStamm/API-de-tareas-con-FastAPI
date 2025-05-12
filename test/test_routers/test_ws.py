import pytest, json
from conftest import auth_headers, client, test_create_project_init, select, db_models
from sqlalchemy.exc import SQLAlchemyError
from fastapi import WebSocketException, WebSocket
from routers import ws
from models import exceptions, schemas
from unittest.mock import AsyncMock
from starlette.requests import Request

def test_websocket_connection(client, auth_headers, test_create_project_init, test_session):
    project_id_to_test = 1 
    user_id_from_token = 1 

    try:
        # Usar solo el header Authorization
        headers = {"Authorization": auth_headers["Authorization"]}

        # Conectar al WebSocket usando el project_id
        with client.websocket_connect(f"/ws/{project_id_to_test}", headers=headers) as websocket: 

            connect_event = websocket.receive_json() # Espera y recibe JSON
            print(f"Received connect event: {connect_event}")

            # Verifica la estructura y contenido del evento de conexión
            assert connect_event["type"] == "user_connected"
            # assert "payload" in connect_event
            
            connect_payload = connect_event["payload"]
            assert connect_payload["user_id"] == user_id_from_token # Verifica que sea el user_id correcto

            message_content_to_send = "Hola desde el test" # Define el contenido del mensaje
            
            # Prepara el payload del mensaje entrante
            message_payload_to_send = schemas.GroupMessagePayload(content=message_content_to_send)
            
            # Prepara el evento completo para enviar
            message_event_to_send = schemas.WebSocketEvent(
                type="group_message",
                payload=message_payload_to_send.model_dump() 
            )

            # Envía el mensaje como JSON
            print(f"Sending message event: {message_event_to_send.model_dump_json()}")
            websocket.send_json(message_event_to_send.model_dump())

            received_event = websocket.receive_json() # Espera y recibe JSON
            print(f"Received broadcast event: {received_event}")

            # Verifica la estructura del evento recibido
            assert received_event["type"] == "group_message"
            assert "payload" in received_event
            received_payload = received_event["payload"]

            assert "id" in received_payload # El ID generado por la base de datos
            assert received_payload["project_id"] == project_id_to_test
            assert received_payload["sender_id"] == user_id_from_token # El servidor asigna el user_id correcto
            assert received_payload["content"] == message_content_to_send # El contenido debe coincidir
            assert "timestamp" in received_payload # Verifica que el timestamp exista

            # Verifica si se guardo el mensaje en la base de datos
            stmt = select(db_models.ProjectChat).where(
                db_models.ProjectChat.project_id == project_id_to_test,
                db_models.ProjectChat.user_id == user_id_from_token,
                db_models.ProjectChat.message == message_content_to_send # Verifica que el contenido guardado coincida
            )
            chat_message = test_session.exec(stmt).first()

            assert chat_message is not None, "El mensaje no se guardó en la base de datos"

    except ws.WebSocketDisconnect as e:
        pytest.fail(f"WebSocket disconnected unexpectedly: code={e.code}, reason={e.reason}")

    except Exception as e:
        pytest.fail(f"An unexpected error occurred during the test: {e}")

def test_get_chat(client, auth_headers, test_create_project_init):
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