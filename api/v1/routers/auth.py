from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timezone
from db.database import get_session, Session, SQLAlchemyError
from passlib.context import CryptContext
from dependency.auth_dependencies import get_auth_serv, AuthService, get_current_user
from models import schemas, responses
from models.exceptions import InvalidToken, UserNotFoundError, DatabaseError
from models.db_models import User
import os
from core.logger import logger
from core.limiter import limiter


router = APIRouter(tags=["Login"])

# Duracion de los tokens
ACCESS_TOKEN_DURATION = int(os.environ.get("ACCESS_TOKEN_DURATION", "15"))
REFRESH_TOKEN_DURATION = int(os.environ.get("REFRESH_TOKEN_DURATION", "7"))

ALGORITHM = os.environ.get("ALGORITHM")

SECRET = os.environ.get("SECRET_KEY")

crypt = CryptContext(schemes=["bcrypt"])

oauth2 = OAuth2PasswordBearer(tokenUrl="token", scheme_name="Bearer")


@router.post(
    "/logout",
    description="Logout path to close session. Close all user sessions ",
    responses={
        200: {"description": "All user sesisons are closed."},
        500: {"detail": "Internal error", "model": responses.DatabaseErrorResponse},
    },
)
@limiter.limit("10/minute")
async def logout(
    request: Request,
    user: User = Depends(get_current_user),
    auth_serv: AuthService = Depends(get_auth_serv),
):
    try:
        return auth_serv.logout(user.user_id)
    except DatabaseError:
        logger.error("[logout] Database Error")
        raise


# @limiter.limit("10/minute")
async def auth_user_ws(token: str, session: Session):
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])

        user_id: str = payload.get("sub")
        if user_id is None:
            return None

        user = session.get(User, int(user_id))
        if user is None:
            return None

        return user

    except JWTError:
        return None


@router.post(
    "/login",
    description="Login path. You need a username and password. First need to create a user",
)
# @limiter.limit("10/minute")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    auth_serv: AuthService = Depends(get_auth_serv),
):
    try:
        return await auth_serv.login(form)
    except DatabaseError:
        logger.error("[login] Database Error")
        raise


@router.post(
    "/refresh",
    description="Refresh path for obtain a new token. You need a refresh token.",
    responses={
        200: {
            "detail": "New access_token and refresh_token obtained",
            "model": schemas.Token,
        },
        401: {"detail": "Token incorrect", "model": responses.InvalidToken},
        404: {"detail": "User not found", "model": responses.NotFound},
        500: {"detail": "Internal error", "model": responses.DatabaseErrorResponse},
    },
)
@limiter.limit("10/minute")
async def refresh(
    refresh: schemas.RefreshTokenRequest,
    request: Request,
    auth_serv: AuthService = Depends(get_auth_serv),
) -> schemas.Token:
    try:
        return auth_serv.refresh(refresh)
    except JWTError as e:
        logger.error(f"[refresh] Invalid Token during refresh | Error :{str(e)}")
        if hasattr(e, "claims"):
            logger.error(f"Problematic claims: {e.claims}")
        raise InvalidToken()

    except DatabaseError:
        logger.error("[refresh] Database Error")
        raise


@router.post(
    "/logout",
    description="Logout path to close session. Close all user sessions ",
    responses={
        200: {"description": "All user sesisons are closed."},
        500: {"detail": "Internal error", "model": responses.DatabaseErrorResponse},
    },
)
@limiter.limit("10/minute")
async def logout(
    request: Request,
    user: User = Depends(get_current_user),
    auth_serv: AuthService = Depends(get_auth_serv),
):
    try:
        return auth_serv.logout(user.user_id)
    except DatabaseError:
        logger.error("[logout] Database Error")
        raise


@router.get("/expired")
def get_expired_sessions(auth_serv: AuthService = Depends(get_auth_serv)):
    try:
        return auth_serv.get_expired_sessions()
    except SQLAlchemyError as e:
        logger.error(f"[get_expired_sessions] Database Error | Error: {str(e)}")
        raise DatabaseError(e, func="get_expired_sessions")
