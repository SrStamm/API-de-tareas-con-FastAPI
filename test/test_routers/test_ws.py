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

from services.chat_services import ChatService


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

def test_get_chat_non_member(mocker):
    mock_user = mocker.Mock(spec=db_models.User)
    mock_user.user_id = 1
    mock_service = mocker.Mock(spec=ChatService)
    mock_service.get_chat.side_effect = exceptions.ProjectNotFoundError(1)

    with pytest.raises(exceptions.ProjectNotFoundError):
        ws.get_chat(
            request=mocker.Mock(spec=Request),
            project_id=1,
            user=mock_user,
            service=mock_service,
        )

@pytest.mark.asyncio
async def test_send_message_to_project_error(mocker):
    user_mock = mocker.Mock(spec=db_models.User)
    user_mock.user_id = 1
    payload = mocker.Mock(spec=schemas.GroupMessagePayload)
    payload.content = "probando"
    service = mocker.Mock(spec=ChatService)
    service.send_message.side_effect = exceptions.DatabaseError(
        Exception("boom"), "save_message"
    )
    broadcast = mocker.patch("api.v1.routers.ws.manager.broadcast", new_callable=AsyncMock)

    with pytest.raises(exceptions.DatabaseError):
        await ws.send_message_to_project(
            project_id=1,
            message_payload=payload,
            user=user_mock,
            service=service,
        )

    broadcast.assert_not_awaited() 

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
