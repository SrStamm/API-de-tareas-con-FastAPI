from db.database import Session, get_session
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dependency.group_dependencies import get_group_service
from models.exceptions import (
    GroupNotFoundError,
    InvalidToken,
    NotAuthorized,
    UserNotFoundError,
    UserNotInGroupError,
)
from repositories.auth_repositories import AuthRepository
from services.auth_services import AuthService
from services.group_service import GroupService
from typing import List, Callable

security = HTTPBearer()


def get_auth_repo(session: Session = Depends(get_session)):
    return AuthRepository(session)


def get_auth_serv(auth_repo: AuthService = Depends(get_auth_repo)) -> AuthService:
    return AuthService(auth_repo)


def get_current_user(
    auth_serv: AuthService = Depends(get_auth_serv),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    try:
        return auth_serv.auth_user(credentials.credentials)
    except UserNotFoundError:
        raise
    except InvalidToken:
        raise


def require_role(roles: List[str]) -> Callable:
    def dependency(
        group_id: int,
        user: User = Depends(get_current_user),
        group_serv: GroupService = Depends(get_group_service),
    ):
        group_found = group_serv.get_group_or_404(group_id)
        if not group_found:
            raise GroupNotFoundError(group_id)

        found_user = group_serv.role_of_user_in_group(user.user_id, group_id)

        if not found_user:
            raise UserNotInGroupError(user_id=user.user_id, group_id=group_id)

        if found_user not in roles:
            raise NotAuthorized(user.user_id)

        return {"user": user, "role": found_user.value}

    return dependency
