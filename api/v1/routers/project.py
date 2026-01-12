from fastapi import APIRouter, Depends, Request
from models import schemas, responses
from models.db_models import User
from typing import List
from core.permission import require_permission, require_role
from core.limiter import limiter
from dependency.auth_dependencies import get_current_user
from dependency.project_dependencies import get_project_service, ProjectService

router = APIRouter(prefix="/project", tags=["Project"])


@router.get(
    "/me",
    summary="Get projects where user is in",
    description="""  Obtained all projects where user is part.
                    'skip' receives an "int" that skips the result obtained.
                    'limit' receives an "int" that limits the result obtained.""",
    responses={
        200: {
            "description": "Projects where user is part obtained",
            "model": schemas.ReadBasicProject,
        },
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("10/minute")
async def get_projects_iam(
    request: Request,
    limit: int = 10,
    skip: int = 0,
    user: User = Depends(get_current_user),
    project_serv: ProjectService = Depends(get_project_service),
) -> List[schemas.ReadBasicProject]:
    return await project_serv.get_projects_iam(user.user_id, limit, skip)


@router.get(
    "/{group_id}/projects",
    summary="Get all projects on the group where I am",
    responses={
        200: {
            "description": "Projects of the group obtained",
            "model": schemas.ReadProject,
        },
        404: {
            "description": "Group or proyects not found",
            "model": responses.NotFound,
        },
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("20/minute")
def get_projects_in_group_where_iam(
    request: Request,
    group_id: int,
    user: User = Depends(get_current_user),
    project_serv: ProjectService = Depends(get_project_service),
) -> List[schemas.ReadProject]:
    return project_serv.get_projects_in_group_where_iam(
        group_id=group_id, user_id=user.user_id
    )


@router.get(
    "/{group_id}",
    summary="Get all projects on the group",
    description=""" Obtained all of projects of the group.
                        'skip' receives an "int" that skips the result obtained.
                        'limit' receives an "int" that limits the result obtained.""",
    responses={
        200: {
            "description": "Projects of the group obtained",
            "model": schemas.ReadProject,
        },
        404: {
            "description": "Group or proyects not found",
            "model": responses.NotFound,
        },
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("20/minute")
async def get_projects(
    request: Request,
    group_id: int,
    limit: int = 10,
    skip: int = 0,
    auth_data: dict = Depends(require_role(roles=["admin"])),
    project_serv: ProjectService = Depends(get_project_service),
) -> List[schemas.ReadProject]:
    return await project_serv.get_all_projects(group_id, limit, skip)


@router.post(
    "/{group_id}",
    summary="Create a new project",
    description="""Allows create an new proyect on the group to authenticated user.
                        To create it, you need an 'title', optional 'description'""",
    responses={
        201: {"description": "Project created", "model": responses.ProjectCreateSucces},
        404: {"description": "Group not found", "model": responses.NotFound},
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("10/minute")
async def create_project(
    request: Request,
    new_project: schemas.CreateProject,
    group_id: int,
    auth_data: dict = Depends(require_role(roles=["admin"])),
    project_serv: ProjectService = Depends(get_project_service),
):
    actual_user: User = auth_data["user"]

    return await project_serv.create_project(group_id, actual_user.user_id, new_project)


@router.patch(
    "/{group_id}/{project_id}",
    summary="Update the project",
    description="""Allows update an proyect of the grupo if user has Administrator permissions on the proyect.
                        Allows modificate 'title' and 'description' """,
    responses={
        200: {"description": "Project updated", "model": responses.ProjectUpdateSucces},
        401: {"description": "User not authorized", "model": responses.NotAuthorized},
        404: {"description": "Group or project not found", "model": responses.NotFound},
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("15/minute")
async def update_project(
    request: Request,
    group_id: int,
    project_id: int,
    updated_project: schemas.UpdateProject,
    auth_data: dict = Depends(require_permission(permissions=["admin", "write"])),
    project_serv: ProjectService = Depends(get_project_service),
):
    return await project_serv.update_project(group_id, project_id, updated_project)


@router.delete(
    "/{group_id}/{project_id}",
    summary="Delete the project",
    description="""Allows remove an project of the group if an authenticated user has Administrator permissions on the proyect""",
    responses={
        200: {"description": "Proyect deleted", "model": responses.ProjectDeleteSucces},
        401: {"description": "User not authorized", "model": responses.NotAuthorized},
        404: {"description": "Group or project not found", "model": responses.NotFound},
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("5/minute")
async def delete_project(
    request: Request,
    group_id: int,
    project_id: int,
    auth_data: dict = Depends(require_permission(permissions=["admin"])),
    project_serv: ProjectService = Depends(get_project_service),
):
    return await project_serv.delete_project(group_id, project_id)


@router.post(
    "/{group_id}/{project_id}/{user_id}",
    summary="Append a user to project",
    description="""Allows an authenticated user with Administrator permissions
                        to add a new user to the proyect if it exists in the group.""",
    responses={
        201: {
            "description": "User added to project",
            "model": responses.ProjectAppendUserSucces,
        },
        400: {"description": "Error in request", "model": responses.ErrorInRequest},
        401: {"description": "User not authorized", "model": responses.NotAuthorized},
        404: {"description": "Group or project not found", "model": responses.NotFound},
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("10/minute")
async def add_user_to_project(
    request: Request,
    group_id: int,
    user_id: int,
    project_id: int,
    auth_data: dict = Depends(require_permission(permissions=["admin"])),
    project_serv: ProjectService = Depends(get_project_service),
):
    return await project_serv.add_user(group_id, project_id, user_id)


@router.delete(
    "/{group_id}/{project_id}/{user_id}",
    summary="Remove a user to project",
    description="""Allow an authenticated user with Administrator permission
                        to remove an user of the proyect""",
    responses={
        200: {
            "description": "User removed of the project",
            "model": responses.ProjectDeleteUserSucces,
        },
        400: {"description": "Error in request", "model": responses.ErrorInRequest},
        401: {
            "description": "User not authenticated",
            "model": responses.NotAuthorized,
        },
        404: {"description": "Group or project not found", "model": responses.NotFound},
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("10/minute")
async def remove_user_from_project(
    request: Request,
    group_id: int,
    project_id: int,
    user_id: int,
    auth_data: dict = Depends(require_permission(permissions=["admin"])),
    project_serv: ProjectService = Depends(get_project_service),
):
    return await project_serv.remove_user(group_id, project_id, user_id)


@router.patch(
    "/{group_id}/{project_id}/{user_id}",
    summary="Update user permissions in the project",
    description="""Allow an authenticated user whit Administrator permission
                        to update a user's permission on a project""",
    responses={
        200: {
            "description": "User's permission on a project updated",
            "model": responses.ProjectUPdateUserSucces,
        },
        400: {"description": "Error in request", "model": responses.ErrorInRequest},
        401: {"description": "User not authorized", "model": responses.NotAuthorized},
        404: {"description": "Group or porject not found", "model": responses.NotFound},
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("15/minute")
async def update_user_permission_in_project(
    request: Request,
    group_id: int,
    user_id: int,
    project_id: int,
    update_role: schemas.UpdatePermissionUser,
    auth_data: dict = Depends(require_permission(permissions=["admin"])),
    project_serv: ProjectService = Depends(get_project_service),
):
    return await project_serv.update_user_permission_in_project(
        group_id, project_id, user_id, update_role
    )


@router.get(
    "/{group_id}/{project_id}/users",
    summary="Get users from the projecy",
    description=""" Obtained all users of the project.
                    'skip' receives an "int" that skips the result obtained.
                    'limit' receives an "int" that limits the result obtained.""",
    responses={
        200: {
            "description": "Users from the project obtained",
            "model": schemas.ReadProjectUser,
        },
        400: {"description": "Error in request", "model": responses.ErrorInRequest},
        404: {
            "description": "Group or project not obtained",
            "model": responses.NotFound,
        },
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("20/minute")
async def get_user_in_project(
    request: Request,
    group_id: int,
    project_id: int,
    limit: int = 10,
    skip: int = 0,
    _: User = Depends(get_current_user),
    project_serv: ProjectService = Depends(get_project_service),
) -> List[schemas.ReadProjectUser]:
    return await project_serv.get_user_in_project(group_id, project_id, limit, skip)


@router.get(
    "/{group_id}/{project_id}/permission",
    summary="Get permission for user in the project",
    responses={
        200: {
            "description": "User's permission from the project obtained",
            "model": schemas.ReadPermissionUser,
        },
        400: {"description": "Error in request", "model": responses.ErrorInRequest},
        404: {
            "description": "Group or project not obtained",
            "model": responses.NotFound,
        },
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("20/minute")
async def get_user_data_in_project(
    request: Request,
    project_id: int,
    user: User = Depends(get_current_user),
    project_serv: ProjectService = Depends(get_project_service),
) -> schemas.ReadPermissionUser:
    return project_serv.get_access_data_in_project(project_id, user.user_id)
