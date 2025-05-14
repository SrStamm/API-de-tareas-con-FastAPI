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
            print(f"Received connection event: {connect_event}")

            assert isinstance(connect_event, dict), "Received connection event is not a dictionary"
            assert "type" in connect_event, "Connection event missing 'type' field"
            assert connect_event["type"] == "user_connected", f"Connection event type is incorrect. Expected 'user_connected', got {connect_event['type']}"
            assert "payload" in connect_event, "Connection event missing 'payload' field"
            assert isinstance(connect_event["payload"], dict), "Connection event payload is not a dictionary"

            # Verifica el contenido del payload del evento de conexión (basado en schemas.Message)
            connect_payload = connect_event["payload"]
            assert "user_id" in connect_payload, "Connection event payload missing 'user_id'"
            assert connect_payload["user_id"] == user_id_from_token, f"Connection event payload user_id is incorrect. Expected {user_id_from_token}, got {connect_payload['user_id']}"
            assert "project_id" in connect_payload, "Connection event payload missing 'project_id'"
            assert connect_payload["project_id"] == project_id_to_test, f"Connection event payload project_id is incorrect. Expected {project_id_to_test}, got {connect_payload['project_id']}"
            assert "timestamp" in connect_payload, "Connection event payload missing 'timestamp'" # Verifica que la clave exista
            assert "content" in connect_payload, "Connection event payload missing 'content'" # Verifica que la clave exista

            message_content_to_send = "Hola desde el test"
            message_payload_to_send = schemas.GroupMessagePayload(content=message_content_to_send)

            message_event_to_send = schemas.WebSocketEvent(
                type="group_message",
                payload=message_payload_to_send.model_dump()
            )

            websocket.send_json(message_event_to_send.model_dump())

            # Recibe el mensaje 
            received_event = websocket.receive_json() # Espera y recibe JSON

            # Verifica la estructura básica del evento recibido
            assert isinstance(received_event, dict), "Received broadcast event is not a dictionary"
            assert "type" in received_event, "Broadcast event missing 'type' field"
            assert received_event["type"] == "group_message", f"Broadcast event type is incorrect. Expected 'group_message', got {received_event['type']}"
            assert "payload" in received_event, "Broadcast event missing 'payload' field"
            assert isinstance(received_event["payload"], dict), "Broadcast event payload is not a dictionary"


            # Verifica los campos del payload saliente 
            received_payload = received_event["payload"]
            assert "id" in received_payload, "Broadcast payload missing 'id' field"
            assert received_payload["project_id"] == project_id_to_test, f"Broadcast payload project_id is incorrect. Expected {project_id_to_test}, got {received_payload['project_id']}"
            assert received_payload["sender_id"] == user_id_from_token, f"Broadcast payload sender_id is incorrect. Expected {user_id_from_token}, got {received_payload['sender_id']}" # El servidor asigna el user_id correcto
            assert received_payload["content"] == message_content_to_send, "Broadcast payload content does not match sent content"
            assert "timestamp" in received_payload, "Broadcast payload missing 'timestamp' field"


            message_content_to_send = "Hola user test"
            received_user_id_test = 2
            message_payload_to_send = schemas.PersonalMessagePayload(content=message_content_to_send, received_user_id=received_user_id_test)

            message_event_to_send = schemas.WebSocketEvent(
                type="personal_message",
                payload=message_payload_to_send.model_dump()
            )

            websocket.send_json(message_event_to_send.model_dump())

    except WebSocketException as e:
        # Captura excepciones de FastAPI/Starlette durante el handshake o manejo inicial
        pytest.fail(f"WebSocket connection failed with WebSocketException: code={e.code}, reason={e.reason}")
    except ws.WebSocketDisconnect as e:
        # Captura la desconexión normal al final del bloque 'with' o una desconexión inesperada antes.
        # Si se llega aquí sin un pytest.fail previo, significa que el bloque 'with' terminó correctamente.
        print(f"WebSocket disconnected: code={e.code}, reason={e.reason}")
        pass 
    except Exception as e:
        # Captura cualquier otra excepción inesperada durante la ejecución del test
        print(f"An unexpected error occurred during the test: {e}")
        pytest.fail(f"Test failed due to unexpected exception: {e}", pytrace=True) # pytrace=True muestra el traceback del test

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

def test_send_message_to_group(client, auth_headers):
    response = client.post('/chat/1', headers=auth_headers, json={'content':'Enviando mensaje por http'})
    assert response.status_code == 200
    assert response.json() == {'detail':'Mensaje enviado con exito al proyecto 1 por user 1'}

@pytest.mark.asyncio
async def test_send_message_to_group(mocker, auth_headers):
    message_mocker = mocker.Mock(spec=schemas.GroupMessagePayload)
    message_mocker.content = 'Probando error en base de datos'

    user_mock = mocker.Mock(spec=db_models.User)
    session_mock = mocker.Mock()

    mocker.patch('routers.ws.found_user_in_project_or_404', return_value=1)

    session_mock.add.side_effect = SQLAlchemyError('Error en base de datos')

    with pytest.raises(exceptions.DatabaseError):
        await ws.send_message_to_group(
            project_id=1,
            message_payload=message_mocker,
            user=user_mock,
            session=session_mock)
    
    session_mock.rollback.assert_called_once()

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