from repositories.auth_repositories import AuthRepository
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from core.logger import logger
from models.exceptions import (
    DatabaseError,
    InvalidToken,
    LoginError,
    SessionNotFound,
    UserNotFoundError,
    UserNotFoundInLogin,
)
from models.schemas import RefreshTokenRequest, Token
import uuid
import os

ACCESS_TOKEN_DURATION = int(os.environ.get("ACCESS_TOKEN_DURATION", "15"))
REFRESH_TOKEN_DURATION = int(os.environ.get("REFRESH_TOKEN_DURATION", "7"))

ALGORITHM = os.environ.get("ALGORITHM")
SECRET = os.environ.get("SECRET_KEY")

crypt = CryptContext(schemes=["bcrypt"])

oauth2 = OAuth2PasswordBearer(tokenUrl="token", scheme_name="Bearer")


class AuthService:
    def __init__(self, auth_repo: AuthRepository):
        self.auth_repo = auth_repo

    def get_expired_sessions(self):
        try:
            exp_sessions = self.auth_repo.get_expired_sessions()
            if exp_sessions:
                logger.info("[AuthService.get_expired_sessions] Expired Sessions Found")
                return exp_sessions

            logger.info("[AuthService.get_expired_sessions]Expired Sessions not Found")
            return {"detail": "No expired sessions"}
        except Exception as e:
            logger.error(f"[AuthService.get_expired_sessions] Unknown error: {e}")
            raise

    def auth_user(self, token: str):
        try:
            # Decodes the token
            payload = jwt.decode(token, SECRET, algorithms=ALGORITHM)

            # Verifies thath the token is an access token
            scope = payload.get("scope")
            if not scope or scope != "api_access":
                logger.error(
                    "[AuthService.auth_user] token Error | Is not a access token"
                )
                raise InvalidToken

            # Get necessary data
            user_id = payload.get("sub")
            if not user_id:
                logger.error("[AuthService.auth_user] Token Error | Missing user data")
                raise InvalidToken

            user = self.auth_repo.get_user_by_id(user_id)
            if not user:
                logger.error(
                    f"[AuthService.auth_user] Error | User {user_id} not found"
                )
                raise UserNotFoundError(user_id)

            exp = payload.get("exp")
            if exp is None:
                logger.error("[AuthService.auth_user] Token Error | No expiration")
                raise InvalidToken

            exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
            if exp_datetime < datetime.now(timezone.utc):
                logger.error("[AuthService.auth_user] Token Error | Token expired")
                raise InvalidToken

            return user
        except JWTError as e:
            logger.error(f"[AuthService.auth_user] Token error | Error: {e}")
            raise InvalidToken

    async def login(self, form: OAuth2PasswordRequestForm):
        try:
            user = self.auth_repo.get_user_whit_username(form.username)
            if not user:
                logger.error("[AuthService.login] Login Error | User not found")
                raise UserNotFoundInLogin

            if not crypt.verify(form.password, user.password):
                logger.error("[AuthService.login] Login Error | Incorrect password")
                raise LoginError(user.user_id)

            # Create access token
            access_expires = datetime.now(timezone.utc) + timedelta(
                minutes=ACCESS_TOKEN_DURATION
            )

            access_token = {
                "sub": str(user.user_id),
                "exp": int(access_expires.timestamp()),
                "scope": "api_access",
            }

            encoded_access_token = jwt.encode(access_token, SECRET, algorithm=ALGORITHM)

            info = self.auth_repo.new_session(
                jti=str(uuid.uuid4()),
                sub=str(user.user_id),
                expires_at=(
                    datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DURATION)
                ),
            )

            # Create refresh token
            refresh_token = {
                "jti": info.jti,
                "sub": info.sub,
                "exp": int(info.expires_at.timestamp()),
                "scope": "token_refresh",
            }

            encoded_refresh_token = jwt.encode(
                refresh_token, SECRET, algorithm=ALGORITHM
            )

            return {
                "access_token": encoded_access_token,
                "token_type": "bearer",
                "refresh_token": encoded_refresh_token,
            }
        except DatabaseError as e:
            logger.error(f"[AuthService.login] DatabaseError Error: {e}")
            raise

    def refresh(self, refresh: RefreshTokenRequest):
        try:
            # Desencrypt the token
            unverified_token = jwt.get_unverified_claims(refresh)
            jti = unverified_token.get("jti")

            actual_session = self.auth_repo.get_session_with_jti(jti)
            if not actual_session:
                logger.error(
                    "[AuthService.refresh] Token error | Not found active session for jti: {jti}"
                )
                raise InvalidToken

            payload = jwt.decode(refresh)

            scope = payload.get("scope")
            if not scope:
                logger.error("[AuthService.refresh] Token error | Not have scope")
                raise InvalidToken

            if scope != "token_refresh":
                logger.error("[AuthService.refresh] Token error | Invalid scope")
                raise InvalidToken

            user_id = payload.get("sub")
            if not user_id:
                logger.error("[AuthService.refresh] Token error | Not have user_id")
                raise InvalidToken

            user = self.auth_repo.get_user_by_id(user_id)
            if not user:
                logger.error(
                    f"[AuthService.refresh] Token error | User {user_id} not found"
                )
                raise UserNotFoundError(user_id)

            exp = payload.get("exp")
            if exp is None:
                logger.error("[AuthService.refresh] Token error | Not have expire date")
                raise InvalidToken

            exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
            if exp_datetime < datetime.now(timezone.utc):
                logger.error("[AuthService.refresh] Token error | Token expired")
                raise InvalidToken

            self.auth_repo.delete_session(actual_session)

            # Create a new token
            access_expires = datetime.now(timezone.utc) + timedelta(
                minutes=ACCESS_TOKEN_DURATION
            )

            access_token = {
                "sub": str(user_id),
                "exp": access_expires.timestamp(),
                "scope": "api_access",
            }
            encoded_access_token = jwt.encode(access_token, SECRET, algorithm=ALGORITHM)

            # Create a new session
            new_session = self.auth_repo.new_session(
                jti=str(uuid.uuid4()),
                sub=str(user_id),
                expires_at=datetime.now(timezone.utc)
                + timedelta(days=REFRESH_TOKEN_DURATION),
            )

            refresh_token = {
                "jti": new_session.jti,
                "sub": new_session.sub,
                "exp": new_session.expires_at.timestamp(),
                "scope": "token_refresh",
            }

            encoded_refresh_token = jwt.encode(
                refresh_token, SECRET, algorithm=ALGORITHM
            )

            return Token(
                access_token=encoded_access_token,
                token_type="bearer",
                refresh_token=encoded_refresh_token,
            )
        except JWTError as e:
            logger.error(f"[AuthService.refresh] JWT Error: {e}")
            raise InvalidToken
        except DatabaseError:
            logger.error("[AuthService.refresh] Database Error")
            raise

    def logout(self, user_id: int):
        try:
            active_sessions = self.auth_repo.get_active_sessions(user_id)
            if not active_sessions:
                logger.error(
                    f"[AuthService.logout] Not found active sessions for User {user_id}"
                )
                raise SessionNotFound(user_id)

            for individual_session in active_sessions:
                self.auth_repo.delete_session(individual_session)

            logger.info(
                f"[AuthService.logout] All sessions are closed - User {user_id} closed {len(active_sessions)} sessions"
            )

            return {"detail": "Closed all sessions"}
        except DatabaseError:
            logger.error("[AuthService.logout] Database Error")
            raise
        except Exception as e:
            logger.error(f"[AuthService.logout] Unknown Error: {e}")
            raise
