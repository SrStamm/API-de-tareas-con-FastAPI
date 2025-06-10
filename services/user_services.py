from repositories.user_repositories import UserRepository
from core.logger import logger
from models.exceptions import (
    DatabaseError,
    UserNotFoundError,
    UserWithUsernameExist,
    UserWithEmailExist,
)
from models.schemas import ReadUser, CreateUser, UpdateUser
from models.db_models import User
from db.database import redis_client, redis
import json


class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def get_user_or_404(self, user_id: int):
        user = self.user_repo.get_user_by_id(user_id)

        if not user:
            logger.error(f"User {user_id} no encontrado")
            raise UserNotFoundError(user_id)

        return user

    def exists_user_with_username_or_email(self, username: str, email: str):
        user_found = self.user_repo.get_user_by_username_or_email(email, username)

        if user_found:
            if user_found.username == username:
                logger.error(
                    "[create_user] User exists error | User with this username exists"
                )
                raise UserWithUsernameExist
            elif user_found.email == email:
                logger.error(
                    "[create_user] User exists error | User with this email exists"
                )
                raise UserWithEmailExist
        return

    async def get_all_users(self, limit: int, skip: int):
        try:
            key = f"users:limit:{limit}:offset:{skip}"
            cached = await redis_client.get(key)
            if cached:
                logger.info(f"[get_users] Cache Hit - Key: {key}")
                return json.loads(cached)

            results = self.user_repo.get_all_users(limit, skip)

            to_cache = [
                ReadUser(user_id=user_id, username=username)
                for user_id, username in results
            ]

            # Guarda la respuesta
            try:
                await redis_client.setex(
                    key,
                    600,
                    json.dumps([user_.model_dump() for user_ in to_cache], default=str),
                )
                logger.info(f"[get_users] Cache Set - Key: {key}")
            except redis.RedisError as e:
                logger.warning(f"[get_users] Cache Fail | Key: {key} | Error: {str(e)}")

            return to_cache

        except Exception as e:
            logger.error(f"[user_services.get_all_users] Unexpected error: {str(e)}")
            raise

    async def create_user(self, new_user: CreateUser):
        try:
            self.exists_user_with_username_or_email(new_user.username, new_user.email)

            self.user_repo.create(new_user)

            try:
                await redis_client.delete("users:limit:*:offset:*")
                logger.info("[create_user] Cache Delete - Key: users:limit:*:offset:*")
            except redis.RedisError as e:
                logger.warning(f"[create_user] Cache Delete Error | Error:  {str(e)}")

            return {"detail": "Se ha creado un nuevo usuario con exito"}
        except DatabaseError as e:
            logger.error(f"[user_services.create_user] Repo failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"[user_services.create_user] Unexpected error: {str(e)}")
            raise

    async def update_user(self, user: User, update_user: UpdateUser):
        try:
            if user.username != update_user.username and update_user.username:
                user.username = update_user.username

                try:
                    await redis_client.delete("users:limit:*:offset:*")
                    logger.info(
                        "[update_user_me] Cache Delete - Key: users:limit:*:offset:*"
                    )
                except redis.RedisError as e:
                    logger.warning(
                        f"[update_user_me] Cache Delete Error | Error: {str(e)}"
                    )

            if user.email != update_user.email and update_user.email:
                user.email = update_user.email

            self.user_repo.session.commit()

            return {"detail": "Se ha actualizado el usuario con exito"}

        except DatabaseError as e:
            logger.error(f"[user_services.update_user] Repo failed: {str(e)}")
            raise
        except Exception:
            raise

    async def delete_user(self, user: User):
        try:
            self.user_repo.delete(user)

            try:
                await redis_client.delete("users:limit:*:offset:*")
                logger.info(
                    "[delete_user_me] Cache Delete | Key: users:limit:*:offset:*"
                )
            except redis.RedisError as e:
                logger.warning(f"[delete_user_me] Cache Delete Error | Error: {str(e)}")

            return {"detail": "Se ha eliminado el usuario"}
        except DatabaseError as e:
            logger.error(f"[user_services.delete_user] Repo failed: {str(e)}")
            raise
        except Exception:
            raise

