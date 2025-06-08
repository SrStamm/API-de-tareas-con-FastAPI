from fastapi import Depends
from db.database import Session, get_session
from services.user_services import UserService
from repositories.user_repositories import UserRepository

def get_user_repository(session: Session = Depends(get_session)):
    return UserRepository(session)

def get_user_service(user_repo: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(user_repo)