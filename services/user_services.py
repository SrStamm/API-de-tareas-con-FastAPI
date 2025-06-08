from repositories.user_repositories import UserRepository
from core.logger import logger
from models import exceptions

class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def get_user_or_404(self, user_id: int):
        user = self.user_repo.get_user_by_id(user_id)

        if not user:
            logger.error(f'User {user_id} no encontrado')
            raise exceptions.UserNotFoundError(user_id)
        
        return user
    