from db.database import Session, select
from models import db_models, exceptions
from core.logger import logger

def get_group_or_404(group_id: int, session: Session):
    statement = select(db_models.Group).where(db_models.Group.group_id == group_id)
    group = session.exec(statement).first()
        
    if not group:
        logger.error(f'Group {group_id} no encontrado')
        raise exceptions.GroupNotFoundError(group_id)
    
    return group

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
    statement = (select(db_models.User).where(db_models.User.user_id == user_id))
        
    user = session.exec(statement).first()

    if not user:
        logger.error(f'User {user_id} no encontrado')
        raise exceptions.UserNotFoundError(user_id)

    return user

def found_user_in_project_or_404(user_id:int, project_id:int, session: Session) -> db_models.User:
    stmt = (select(db_models.project_user).where(
                    db_models.project_user.user_id == user_id,
                    db_models.project_user.project_id == project_id))
    
    user = session.exec(stmt).first()
    
    if not user:
        logger.error(f'User {user_id} no encontrado en project {project_id}')
        raise exceptions.UserNotInProjectError(user_id=user_id, project_id=project_id)
    
    return user

def found_task_or_404(project_id:int, task_id: int, session: Session) -> db_models.Task:
    stmt = (select(db_models.Task)
            .where(db_models.Task.project_id == project_id, db_models.Task.task_id == task_id))
    
    task_found = session.exec(stmt).first()
    
    if not task_found:
        logger.error(f'Task {task_id} no encontrado en Project {project_id}')
        raise exceptions.TaskNotFound(task_id=task_id, project_id=project_id)
    
    return task_found

def is_admin_in_group(user: db_models.User, group_id: int, session: Session):
    stmt = (select(db_models.group_user)
                    .where(db_models.group_user.user_id == user.user_id, db_models.group_user.group_id == group_id))

    found_user = session.exec(stmt).first()

    if not found_user:
        logger.error(f'User {user.user_id} no encontrado en Group {group_id}')
        raise exceptions.UserNotInGroupError(user_id=user.user_id, group_id=group_id)

    if found_user.role != db_models.Group_Role.ADMIN:
        logger.error(f'User {user.user_id} no esta autorizado en Group {group_id}')
        raise exceptions.NotAuthorized(found_user.user_id)

def is_admin_in_project(user: db_models.User, project_id, session: Session):
    stmt = (select(db_models.project_user).where(
        db_models.project_user.user_id == user.user_id,
        db_models.project_user.project_id == project_id))
    
    resultado = session.exec(stmt).first()

    if not resultado or resultado.permission != db_models.Project_Permission.ADMIN:
        logger.error(f'User {user.user_id} no esta autorizado en Project {project_id}')
        raise exceptions.NotAuthorized(user.user_id)