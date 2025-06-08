from db.database import Session, select, selectinload
from models import db_models, exceptions
from .logger import logger
from db.database import select, Session, select
from typing import List
import re
from repositories.group_repositories import GroupRepository
from fastapi import Depends



def found_project_or_404(group_id:int, project_id:int, session: Session):
    stmt = (select(db_models.Project)
            .where(db_models.Project.group_id == group_id, db_models.Project.project_id == project_id))
    
    founded_project = session.exec(stmt).first()
    
    if not founded_project:
        logger.error(f'Project {project_id} no encontrado')
        raise exceptions.ProjectNotFoundError(project_id)
    
    return founded_project

def found_project_for_task_or_404(project_id:int, session: Session):
    stmt = (select(db_models.Project)
            .where(db_models.Project.project_id == project_id))
    
    founded_project = session.exec(stmt).first()
    
    if not founded_project:
        logger.error(f'Project {project_id} no encontrado')
        raise exceptions.ProjectNotFoundError(project_id)
    
    return founded_project

def get_user_or_404(user_id: int, session: Session):
    stmt = (select(db_models.User).where(db_models.User.user_id == user_id))
    user = session.exec(stmt).first()

    if not user:
        logger.error(f'User {user_id} no encontrado')
        raise exceptions.UserNotFoundError(user_id)

    return user

def found_user_in_project_or_404(user_id:int, project_id:int, session: Session) -> db_models.User:
    stmt = (select(db_models.project_user)
            .where( db_models.project_user.user_id == user_id,
                    db_models.project_user.project_id == project_id))
    
    user = session.exec(stmt).first()
    
    if not user:
        logger.error(f'User {user_id} no encontrado en project {project_id}')
        raise exceptions.UserNotInProjectError(user_id=user_id, project_id=project_id)
    
    return user

def found_task_or_404(project_id:int, task_id: int, session: Session) -> db_models.Task:
    stmt = (select(db_models.Task)
            .where( db_models.Task.project_id == project_id,
                    db_models.Task.task_id == task_id))
    
    task_found = session.exec(stmt).first()
    
    if not task_found:
        logger.error(f'Task {task_id} no encontrado en Project {project_id}')
        raise exceptions.TaskNotFound(task_id=task_id, project_id=project_id)
    
    return task_found

def found_user_in_task_or_404(user_id:int, task_id: int, session: Session):
    stmt = (select(db_models.Task)
            .options(selectinload(db_models.Task.asigned))
            .where(db_models.Task.task_id == task_id))

    found_users_assigned = session.exec(stmt).first()

    if not found_users_assigned: 
        logger.error(f'Task {task_id} no encontrado')
        raise exceptions.TaskErrorNotFound(task_id)

    user_found = session.get(db_models.User, user_id)

    for user in found_users_assigned.asigned:
        if user.username == user_found.username and user.user_id == user_id:
            return
    
    raise exceptions.TaskIsNotAssignedError(task_id, user_id)

def extract_valid_mentions(content: str, session: Session) -> List[db_models.User]:
    mentions_raw = re.findall(r'@(\w+)', content)
    mentions = list(set(mentions_raw))
    
    if not mentions:
        return []
    
    stmt = select(db_models.User.username).where(db_models.User.username.in_(mentions))
    return session.exec(stmt).all()

def validate_in_task(users: List[db_models.User], task_id: int, session:Session):
    stmt = (select(db_models.User.username, db_models.User.user_id)
            .where(
                db_models.tasks_user.user_id == db_models.User.user_id,
                db_models.tasks_user.task_id == task_id,
                db_models.User.username.in_(users)))
    
    return session.exec(stmt).all()