import pytest

from models import exceptions, schemas
from repositories.chat_repositories import ChatRepository
from services.chat_services import ChatService
from services.project_services import ProjectService


def _build_service(mocker):
    repo = mocker.Mock(spec=ChatRepository)
    project_service = mocker.Mock(spec=ProjectService)
    return ChatService(repo, project_service), repo, project_service


def test_get_chat_non_member_returns_not_found(mocker):
    service, repo, project_service = _build_service(mocker)
    project_service.found_user_in_project_or_404.side_effect = (
        exceptions.UserNotInProjectError(1, 1)
    )

    with pytest.raises(exceptions.ProjectNotFoundError):
        service.get_chat(project_id=1, user_id=1, limit=100, skip=0)

    repo.get_chat.assert_not_called()


def test_get_chat_empty_returns_not_found(mocker):
    service, repo, project_service = _build_service(mocker)
    project_service.found_user_in_project_or_404.return_value = None
    repo.get_chat.return_value = []

    with pytest.raises(exceptions.ChatNotFoundError):
        service.get_chat(project_id=1, user_id=1, limit=100, skip=0)


def test_send_message_non_member_returns_not_found(mocker):
    service, repo, project_service = _build_service(mocker)
    project_service.found_user_in_project_or_404.side_effect = (
        exceptions.UserNotInProjectError(1, 1)
    )
    payload = mocker.Mock(spec=schemas.GroupMessagePayload)
    payload.content = "hola"

    with pytest.raises(exceptions.ProjectNotFoundError):
        service.send_message(project_id=1, user_id=1, payload=payload)

    repo.save_message.assert_not_called()
