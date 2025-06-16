from fastapi import Depends
from db.database import Session, get_session
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.exceptions import InvalidToken, UserNotFoundError
from repositories.auth_repositories import AuthRepository
from services.auth_services import AuthService

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
