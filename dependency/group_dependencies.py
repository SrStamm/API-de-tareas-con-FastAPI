from fastapi import Depends
from db.database import Session, get_session
from repositories import group_repositories, user_repositories
from services.group_service import GroupService
from .user_dependencies import get_user_repository


def get_group_repository(session: Session = Depends(get_session)):
    return group_repositories.GroupRepository(session)


def get_group_service(
    group_repo: group_repositories.GroupRepository = Depends(get_group_repository),
    user_repo: user_repositories.UserRepository = Depends(get_user_repository),
) -> GroupService:
    return GroupService(group_repo, user_repo)
