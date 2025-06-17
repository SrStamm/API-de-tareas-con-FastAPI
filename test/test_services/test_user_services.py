from models.exceptions import (
    DatabaseError,
    UserNotFoundError,
    UserWithEmailExist,
    UserWithUsernameExist,
)
from models.schemas import CreateUser
from services.user_services import UserService
from db.database import SQLAlchemyError
import pytest


def test_get_user_or_404_error(mocker):
    mock_user_repo = mocker.Mock()

    mock_user_repo.get_user_by_id.return_value = None

    service = UserService(mock_user_repo)

    with pytest.raises(UserNotFoundError):
        service.get_user_or_404(1)


def test_exists_user_with_username_or_email_error(mocker):
    mock_user_repo = mocker.Mock()

    mock_user = mocker.Mock()
    mock_user.username = "mirko"
    mock_user.email = "falso@gmail.com"

    service = UserService(mock_user_repo)

    mock_user_repo.get_user_by_username_or_email.return_value = mock_user

    with pytest.raises(UserWithUsernameExist):
        service.exists_user_with_username_or_email(
            username="mirko", email="mirko@gmail.com"
        )

    mock_user.email = "mirko@gmail.com"
    mock_user.username = "Falso"

    mock_user_repo.get_user_by_username_or_email.return_value = mock_user

    with pytest.raises(UserWithEmailExist):
        service.exists_user_with_username_or_email(
            username="mirko", email="mirko@gmail.com"
        )


@pytest.mark.asyncio
async def test_create_user_error(mocker):
    mock_user_repo = mocker.Mock()

    mock_new_user = mocker.Mock()

    mock_new_user.username = "falso"
    mock_new_user.email = "falso@gmail.com"
    mock_new_user.password = "falso"

    service = UserService(mock_user_repo)

    mock_user_repo.create.side_effect = DatabaseError(
        SQLAlchemyError("db error"), "create"
    )
    with pytest.raises(DatabaseError):
        await service.create_user(mock_new_user)


@pytest.mark.asyncio
async def test_update_user_error(mocker):
    mock_user_repo = mocker.Mock()

    mock_user = mocker.Mock()
    mock_user.username = "falsisimo"

    mock_update = mocker.Mock()
    mock_update.username = "falso"

    service = UserService(mock_user_repo)

    mock_user_repo.update.side_effect = DatabaseError(
        SQLAlchemyError("db error"), "update"
    )
    with pytest.raises(DatabaseError):
        await service.update_user(mock_user, mock_update)


@pytest.mark.asyncio
async def test_delete_user_error(mocker):
    mock_user_repo = mocker.Mock()

    mock_user = mocker.Mock()

    service = UserService(mock_user_repo)

    mock_user_repo.delete.side_effect = DatabaseError(
        SQLAlchemyError("db error"), "update"
    )
    with pytest.raises(DatabaseError):
        await service.delete_user(mock_user)
