from fastapi import Depends
from db.database import Session, get_session
from repositories import task_repositories
from dependency import user_dependencies, project_dependencies
from services.task_services import TaskService

def get_task_repository(session: Session = Depends(get_session)):
    return task_repositories.TaskRepository(session)

def get_task_service(
        task_repo: task_repositories.TaskRepository = Depends(get_task_repository),
        user_ser: user_dependencies.UserService = Depends(user_dependencies.get_user_service),
        proj_ser: project_dependencies.ProjectService = Depends(project_dependencies.get_project_service),
        ) -> TaskService:
    return TaskService(task_repo, user_ser, proj_ser)