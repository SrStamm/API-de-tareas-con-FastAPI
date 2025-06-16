from fastapi import Depends
from db.database import Session, get_session
from repositories.project_repositories import ProjectRepository
from services.project_services import ProjectService
from services.group_service import GroupService
from services.user_services import UserService
from dependency.group_dependencies import get_group_service
from dependency.user_dependencies import get_user_service

def get_project_repository(session: Session = Depends(get_session)):
    return ProjectRepository(session)

def get_project_service(
        project_repo: ProjectRepository = Depends(get_project_repository),
        user_serv: UserService = Depends(get_user_service),
        group_serv: GroupService = Depends(get_group_service)) -> ProjectService:
    return ProjectService(project_repo, group_serv, user_serv)