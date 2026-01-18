from fastapi import Depends
from models.exceptions import (
    GroupNotFoundError,
    UserNotInGroupError,
    NotAuthorized,
    UserNotInProjectError,
)
from models.schemas import ReadUser
from typing import Callable, List
from dependency.project_dependencies import get_project_repository
from dependency.group_dependencies import GroupService, get_group_service
from dependency.auth_dependencies import get_current_user
from repositories.project_repositories import ProjectRepository


def require_role(roles: List[str]) -> Callable:
    def dependency(
        group_id: int,
        user: ReadUser = Depends(get_current_user),
        group_serv: GroupService = Depends(get_group_service),
    ):
        group_found = group_serv.get_group_or_404(group_id)
        if not group_found:
            raise GroupNotFoundError(group_id)

        found_user = group_serv.role_of_user_in_group(user.user_id, group_id)

        if not found_user:
            raise UserNotInGroupError(user_id=user.user_id, group_id=group_id)

        if found_user not in roles:
            raise NotAuthorized(user.user_id)

        return {"user": user, "role": found_user.value}

    return dependency


def role_of_user_in_group(
    user_id: int, group_id: int, group_serv: GroupService = Depends(get_group_service)
):
    found_user = group_serv.role_of_user_in_group(user_id, group_id)

    if not found_user:
        raise UserNotInGroupError(user_id=user_id, group_id=group_id)

    return found_user.value


def require_permission(permissions: List[str]) -> Callable:
    def dependency(
        project_id: int,
        user: ReadUser = Depends(get_current_user),
        project_repo: ProjectRepository = Depends(get_project_repository),
    ):
        found_user = project_repo.get_user_in_project(project_id, user.user_id)

        if not found_user:
            raise UserNotInProjectError(user_id=user.user_id, project_id=project_id)

        if found_user.permission not in permissions:
            raise NotAuthorized(user.user_id)

        return {"user": user, "permission": found_user.permission.value}

    return dependency


def permission_of_user_in_project(
    user_id: int,
    project_id: int,
    project_repo: ProjectRepository = Depends(get_project_repository),
):
    found_user = project_repo.get_user_in_project(project_id, user_id)

    if not found_user:
        raise UserNotInProjectError(user_id=user_id, project_id=project_id)

    return found_user.permission.value
