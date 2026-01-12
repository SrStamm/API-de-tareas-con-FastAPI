from fastapi import APIRouter, Depends, Request
from models import schemas, responses
from models.db_models import User
from typing import List
from core.permission import require_role
from core.limiter import limiter
from dependency.group_dependencies import get_group_service, GroupService
from dependency.auth_dependencies import get_current_user

router = APIRouter(prefix="/group", tags=["Group"])


@router.get(
    "",
    summary="Obtain all groups",
    description=""" Obtain all groups with paginated with name and her users.
                        'skip' is a value to skip the results obtained.
                        'limit' is a value to limit the result obtained.""",
    responses={
        200: {"description": "Groups obtained", "model": schemas.ReadBasicDataGroup},
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("60/minute")
async def get_groups(
    request: Request,
    limit: int = 10,
    skip: int = 0,
    group_service: GroupService = Depends(get_group_service),
) -> List[schemas.ReadBasicDataGroup]:
    return await group_service.get_groups_with_cache(limit, skip)


@router.post(
    "",
    summary="Create a new group",
    description=""" The authenticated user creates a new group, needs a 'name', and an optional 'description'.
                        The user is automatically part of the group """,
    responses={
        201: {"description": "Group created"},
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("15/minute")
async def create_group(
    request: Request,
    new_group: schemas.CreateGroup,
    user: User = Depends(get_current_user),
    group_service: GroupService = Depends(get_group_service),
) -> schemas.ReadGroup:
    return await group_service.create_group(new_group, user.user_id)


@router.patch(
    "/{group_id}",
    summary="Update the group",
    description="""
        Allows an authenticated user with Administrator or Editor rol to change group information,
        such as 'name' or 'description'""",
    responses={
        200: {"description": "Group updated", "model": responses.GroupUpdateSucces},
        401: {"description": "User not authorized", "model": responses.NotAuthorized},
        404: {"description": "Group not Found", "model": responses.NotFound},
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("15/minute")
async def update_group(
    request: Request,
    group_id: int,
    updated_group: schemas.UpdateGroup,
    auth_data: dict = Depends(require_role(roles=["admin", "editor"])),
    group_service: GroupService = Depends(get_group_service),
) -> schemas.ReadGroup:
    actual_role = auth_data["role"]
    actual_user = auth_data["user"]

    return await group_service.update_group(
        group_id, updated_group, actual_role, actual_user.user_id
    )


@router.delete(
    "/{group_id}",
    summary="Delete the group",
    description="Allows an authenticated user with Administrator or Editor rol to delete the group.",
    responses={
        200: {"description": "Group deleted", "model": responses.GroupDeleteSucces},
        401: {"description": "User not authorized", "model": responses.NotAuthorized},
        404: {"description": "Group not found", "model": responses.NotFound},
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("5/minute")
async def delete_group(
    request: Request,
    group_id: int,
    _: dict = Depends(require_role(roles=["admin"])),
    group_service: GroupService = Depends(get_group_service),
):
    return await group_service.delete_group(group_id)


@router.get(
    "/me",
    summary="Get the groups the user is in",
    description=""" Read all groups where user is part with limit information.
                        'skip' receives an "int" that skips the result obtained.
                        'limit' receives an "int" that limits the result obtained.""",
    responses={
        200: {
            "description": "Groups to which the user belongs obtained",
            "model": schemas.ReadGroup,
        },
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("60/minute")
async def get_groups_in_user(
    request: Request,
    limit: int = 10,
    skip: int = 0,
    user: User = Depends(get_current_user),
    group_service: GroupService = Depends(get_group_service),
) -> List[schemas.ReadGroup]:
    return await group_service.get_groups_where_user_in(user.user_id, limit, skip)


@router.post(
    "/{group_id}/{user_id}",
    summary="Append a new user to group",
    description="Allows an authenticated user with Administrator or Editor rol to append a new user to group.",
    responses={
        201: {
            "description": "User added to group",
            "model": responses.GroupAppendUserSucces,
        },
        400: {"description": "request error", "model": responses.ErrorInRequest},
        401: {"description": "User not authorized", "model": responses.NotAuthorized},
        404: {"description": "Group not found", "model": responses.NotFound},
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("20/minute")
async def append_user_group(
    request: Request,
    group_id: int,
    user_id: int,
    _: dict = Depends(require_role(roles=["admin", "editor"])),
    group_service: GroupService = Depends(get_group_service),
):
    return await group_service.append_user(group_id, user_id)


@router.delete(
    "/{group_id}/{user_id}",
    summary="Remove a user to group",
    description="Allows an authenticated user with Administrator or Editor role to remove a user from a group.",
    responses={
        200: {
            "description": "User removed from the group",
            "model": responses.GroupDeleteUserSucces,
        },
        400: {"description": "request error", "model": responses.ErrorInRequest},
        401: {"description": "User not authorized", "model": responses.NotAuthorized},
        404: {"description": "Group not found", "model": responses.NotFound},
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("5/minute")
async def delete_user_group(
    request: Request,
    group_id: int,
    user_id: int,
    auth_data: dict = Depends(require_role(roles=["admin", "editor"])),
    group_service: GroupService = Depends(get_group_service),
):
    actual_role = auth_data["role"]
    actual_user: User = auth_data["user"]

    return await group_service.delete_user(
        group_id=group_id,
        user_id=user_id,
        actual_user_id=actual_user.user_id,
        actual_user_role=actual_role,
    )


@router.patch(
    "/{group_id}/{user_id}",
    summary="Update role of user in group",
    description="Permite al usuario autenticado con rol Administrador el modificar el rol de un usuario en el grupo",
    responses={
        200: {
            "description": "Usuario actualizado en el Grupo",
            "model": responses.GroupUPdateUserSucces,
        },
        400: {"description": "request error", "model": responses.ErrorInRequest},
        401: {"description": "Usuario no autorizado", "model": responses.NotAuthorized},
        404: {"description": "Grupo no encontrado", "model": responses.NotFound},
        500: {"description": "error interno", "model": responses.DatabaseErrorResponse},
    },
)
@limiter.limit("10/minute")
async def update_user_group(
    request: Request,
    group_id: int,
    user_id: int,
    update_role: schemas.UpdateRoleUser,
    _: dict = Depends(require_role(roles=["admin"])),
    group_service: GroupService = Depends(get_group_service),
):
    return await group_service.update_user_role(group_id, user_id, update_role.role)


@router.get(
    "/{group_id}/users",
    summary="Get users in the group",
    description=""" Obtained all the users of the group.
                        'skip' receives an "int" that skips the result obtained.
                        'limit' receives an "int" that limits the result obtained.""",
    responses={
        200: {
            "description": "Usuarios del Grupo obtenidos",
            "model": schemas.ReadGroupUser,
        },
        404: {"description": "Grupo no encontrado", "model": responses.NotFound},
        500: {"description": "error interno", "model": responses.DatabaseErrorResponse},
    },
)
@limiter.limit("60/minute")
async def get_user_in_group(
    request: Request,
    group_id: int,
    _: User = Depends(get_current_user),
    group_service: GroupService = Depends(get_group_service),
) -> List[schemas.ReadGroupUser]:
    return await group_service.get_users_in_group(group_id)


@router.get(
    "/{group_id}/role",
    summary="Get role for user in the group",
    responses={
        200: {
            "description": "Rol del Usuario en el Grupo obtenido",
            "model": schemas.ReadRoleUser,
        },
        500: {"description": "error interno", "model": responses.DatabaseErrorResponse},
    },
)
@limiter.limit("60/minute")
async def get_user_role_in_group(
    request: Request,
    group_id: int,
    user: User = Depends(get_current_user),
    group_service: GroupService = Depends(get_group_service),
) -> schemas.ReadRoleUser:
    return group_service.get_user_data_for_group(user.user_id, group_id)
