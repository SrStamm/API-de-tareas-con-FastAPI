import pytest
from conftest import (
    auth_headers,
    client,
    test_create_project_init,
    db_models,
    async_client,
)
from sqlalchemy.exc import SQLAlchemyError
from fastapi import WebSocketException, WebSocket
from api.v1.routers import ws
from models import exceptions, schemas
from unittest.mock import AsyncMock
from starlette.requests import Request


@pytest.mark.asyncio
async def test_send_message_to_project(
    async_client, auth_headers, test_create_project_init
):
    response = await async_client.post(
        "/chat/1",
        headers=auth_headers,
        json={"content": "Enviando mensaje por http", "project_id": 1},
    )
    assert response.status_code == 200
    assert response.json() == {
        "detail": "Mensaje enviado con exito al proyecto 1 por user 1"
    }


def test_get_chat(client, auth_headers):
    response = client.get("/chat/1", headers=auth_headers)
    assert response.status_code == 200
    messages = response.json()
    assert isinstance(messages, list)
    for message in messages:
        assert all(
            key in message
            for key in ["chat_id", "project_id", "user_id", "message", "timestamp"]
        )


def test_get_chat_error(mocker):
    session_mock = mocker.Mock()
    mock_user = mocker.Mock(spec=db_models.User)
    mock_request = mocker.Mock(spec=Request)

    # Excepcion chat no encontrado
    session_mock.exec.return_value.all.return_value = []

    with pytest.raises(exceptions.ChatNotFoundError):
        ws.get_chat(
            request=mock_request, project_id=1, user=mock_user, session=session_mock
        )

    # Prueba la excepcion de DB
    session_mock.exec.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        ws.get_chat(
            request=mock_request, project_id=1, user=mock_user, session=session_mock
        )


@pytest.mark.asyncio
async def test_send_message_to_project_error(mocker, auth_headers):
    message_mocker = mocker.Mock(spec=schemas.GroupMessagePayload)
    message_mocker.content = "Probando error en base de datos"

    user_mock = mocker.Mock(spec=db_models.User)
    session_mock = mocker.Mock()

    mocker.patch("api.v1.routers.ws.found_user_in_project_or_404", return_value=1)

    session_mock.add.side_effect = SQLAlchemyError("Error en base de datos")

    with pytest.raises(exceptions.DatabaseError):
        await ws.send_message_to_project(
            project_id=1,
            message_payload=message_mocker,
            user=user_mock,
            session=session_mock,
        )

    session_mock.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_get_current_user_ws_header_error(mocker):
    session_mock = mocker.Mock()

    ws_mock = mocker.Mock(spec=WebSocket)
    ws_mock.headers = {}
    ws_mock.close = AsyncMock()

    with pytest.raises(WebSocketException):
        await ws.get_current_user_ws(session=session_mock, websocket=ws_mock)

    ws_mock.close.assert_awaited_once_with(code=1008, reason="User not found for token")


@pytest.mark.asyncio
async def test_get_current_user_ws_format_error(mocker):
    session_mock = mocker.Mock()

    ws_mock = mocker.Mock(spec=WebSocket)
    ws_mock.headers = {"Authorization": "hola"}
    ws_mock.close = AsyncMock()

    with pytest.raises(WebSocketException):
        await ws.get_current_user_ws(session=session_mock, websocket=ws_mock)

    ws_mock.close.assert_awaited_once_with(code=1008, reason="User not found for token")


@pytest.mark.asyncio
async def test_get_current_user_ws_user_not_found_error(mocker):
    session_mock = mocker.Mock()

    ws_mock = mocker.Mock(spec=WebSocket)
    ws_mock.headers = {"Authorization": "Bearer "}
    ws_mock.close = AsyncMock()

    with pytest.raises(WebSocketException):
        await ws.get_current_user_ws(session=session_mock, websocket=ws_mock)

    ws_mock.close.assert_awaited_once_with(code=1008, reason="User not found for token")
