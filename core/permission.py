from fastapi import Depends
from db.database import Session, select
from models import db_models, exceptions
from .logger import logger
from typing import Callable
from api.v1.routers.auth import auth_user
from db.database import select, get_session, Session, select
from typing import List

def require_role(roles: List[str]) -> Callable:
    def dependency( group_id: int,
                    user: db_models.User = Depends(auth_user),
                    session: Session = Depends(get_session)):

        group_found = session.get(db_models.Group, group_id)

        if not group_found:
            raise exceptions.GroupNotFoundError(group_id)

        stmt = (select(db_models.group_user).where(
                    db_models.group_user.user_id == user.user_id,
                    db_models.group_user.group_id == group_id))

        found_user = session.exec(stmt).first()

        if not found_user:
            raise exceptions.UserNotInGroupError(user_id=user.user_id, group_id=group_id)

        if found_user.role not in roles:
            raise exceptions.NotAuthorized(user.user_id)

        return {'user':user, 'role':found_user.role.value}

    return dependency

def role_of_user_in_group(user_id: int, group_id: int, session:Session):
    stmt = (select(db_models.group_user).where(
            db_models.group_user.user_id == user_id,
            db_models.group_user.group_id == group_id))

    found_user = session.exec(stmt).first()

    if not found_user:
        raise exceptions.UserNotInGroupError(user_id=user_id, group_id=group_id)

    return found_user.role.value

def require_permission(permissions: List[str]) -> Callable:
    def dependency( project_id: int,
                    user: db_models.User = Depends(auth_user),
                    session: Session = Depends(get_session)):
        
        project_found = session.get(db_models.Project, project_id)

        if not project_found:
            raise exceptions.ProjectNotFoundError(project_id)

        stmt = (select(db_models.project_user)
                .where( db_models.project_user.user_id == user.user_id,
                        db_models.project_user.project_id == project_id))

        found_user = session.exec(stmt).first()

        if not found_user:
            raise exceptions.UserNotInProjectError(user_id=user.user_id, project_id=project_id)

        if found_user.permission not in permissions:
            raise exceptions.NotAuthorized(user.user_id)

        return {'user':user, 'permission':found_user.permission.value}

    return dependency

def permission_of_user_in_project(user_id: int, project_id: int, session:Session):
    stmt = (select(db_models.project_user)
            .where( db_models.project_user.user_id == user_id,
                    db_models.project_user.project_id == project_id))

    found_user = session.exec(stmt).first()

    if not found_user:
        raise exceptions.UserNotInProjectError(user_id=user_id, project_id=project_id)

    return found_user.permission.value