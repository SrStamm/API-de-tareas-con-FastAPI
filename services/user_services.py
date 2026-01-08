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
            return self.user_repo.get_all_users(limit, skip)

        except Exception as e:
            logger.error(f"[user_services.get_all_users] Unexpected error: {str(e)}")
            raise

    async def create_user(self, new_user: CreateUser):
        try:
            self.exists_user_with_username_or_email(new_user.username, new_user.email)

            self.user_repo.create(new_user)

            return {"detail": "Se ha creado un nuevo usuario con exito"}
        except DatabaseError as e:
            logger.error(f"[user_services.create_user] Repo failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"[user_services.create_user] Unexpected error: {str(e)}")
            raise

    async def update_user(self, user: User, update_user: UpdateUser):
        try:
            self.user_repo.update(user=user, update_user=update_user)
            return {"detail": "Se ha actualizado el usuario con exito"}

        except DatabaseError as e:
            logger.error(f"[user_services.update_user] Repo failed: {str(e)}")
            raise
        except Exception:
            raise

    async def delete_user(self, user: User):
        try:
            self.user_repo.delete(user)
            return {"detail": "Se ha eliminado el usuario"}
        except DatabaseError as e:
            logger.error(f"[user_services.delete_user] Repo failed: {str(e)}")
            raise
        except Exception:
            raise
