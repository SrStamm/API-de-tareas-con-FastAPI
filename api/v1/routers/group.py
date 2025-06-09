from fastapi import APIRouter, Depends, Request
from models import schemas, exceptions, responses
from models.db_models import User
from db.database import SQLAlchemyError
from typing import List
from .auth import auth_user
from core.permission import require_role
from core.logger import logger
from core.limiter import limiter
from dependency.group_dependencies import get_group_service, GroupService

router = APIRouter(prefix='/group', tags=['Group'])

@router.get(
        '',
        description=""" Read all groups with limited data.
                        'skip' receives an "int" that skips the result obtained.
                        'limit' receives an "int" that limits the result obtained.""",
        responses={
            200:{'description':'Groups obtained', 'model':schemas.ReadBasicDataGroup},
            500:{'description':'Internal error', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("60/minute")
async def get_groups(
        request: Request,
        limit:int = 10,
        skip: int = 0,
        group_service: GroupService = Depends(get_group_service)) -> List[schemas.ReadBasicDataGroup]:

    try:
        return await group_service.get_groups_with_cache(limit, skip)

    except SQLAlchemyError as e:
        logger.error(f'[get_groups] Database Error:  {str(e)}')
        raise exceptions.DatabaseError(error=e, func='get_groups')
    except Exception as e:
        logger.error(f'[get_groups] Unexpected Error:  {str(e)}')
        raise

@router.post(
        '',
        description=""" The authenticated user creates a new group, needs a 'name' string, and an optional 'description' string.
                        The user is automatically part of the group """,
        responses={
            201:{'description':'Group created', 'model':responses.GroupCreateSucces},
            500:{'description':'Internal error', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("15/minute")
async def create_group(
        request: Request,
        new_group: schemas.CreateGroup,
        user: User = Depends(auth_user),
        group_service: GroupService = Depends(get_group_service)):
    try:
        return await group_service.create_group(new_group, user.user_id)
    except SQLAlchemyError as e:
        logger.error(f'[create_group] Database Error:  {str(e)}')
        raise exceptions.DatabaseError(error=e, func='get_groups')
    except Exception as e:
        logger.error(f'[create_group] Unexpected Error:  {str(e)}')
        raise

@router.patch(
        '/{group_id}',
        description="""
        Allows an authenticated user with Administrator or Editor rol to change group information,
        such as 'name' or 'description'""",
        responses={
            200:{'description':'Group updated', 'model':responses.GroupUpdateSucces},
            401:{'description':'User not authorized', 'model':responses.NotAuthorized},
            404:{'description':'Group not Found', 'model':responses.NotFound},
            500:{'description':'Internal error', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("15/minute")
async def update_group(
        request: Request,
        group_id: int,
        updated_group: schemas.UpdateGroup,
        auth_data: dict = Depends(require_role(roles=['admin', 'editor'])),
        group_service: GroupService = Depends(get_group_service)):

    try:
        actual_role = auth_data['role']
        actual_user_id = auth_data['user']

        return await group_service.update_group(group_id, updated_group, actual_role, actual_user_id)

    except SQLAlchemyError as e:
        logger.error(f'[update_group] Database Error:  {str(e)}')
        raise exceptions.DatabaseError(error=e, func='get_groups')
    except Exception as e:
        logger.error(f'[update_group] Unexpected Error:  {str(e)}')
        raise

@router.delete(
        '/{group_id}',
        description='Allows an authenticated user with Administrator or Editor rol to delete the group.',
        responses={
            200:{'description':'Group deleted', 'model':responses.GroupDeleteSucces},
            401:{'description':'User not authorized', 'model':responses.NotAuthorized},
            404:{'description':'Group not found', 'model':responses.NotFound},
            500:{'description':'Internal error', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("5/minute")
async def delete_group(
        request: Request,
        group_id: int,
        auth_data: dict = Depends(require_role(roles=['admin'])),
        group_service: GroupService = Depends(get_group_service)):

    try:
        return await group_service.delete_group(group_id)

    except SQLAlchemyError as e:
        logger.error(f'[delete_group] Database Error:  {str(e)}')
        raise exceptions.DatabaseError(error=e, func='get_groups')
    except Exception as e:
        logger.error(f'[delete_group] Unexpected Error:  {str(e)}')
        raise

@router.get(
        '/me',
        description=""" Read all groups where user is part with limit information.
                        'skip' receives an "int" that skips the result obtained.
                        'limit' receives an "int" that limits the result obtained.""",
        responses={
            200:{'description':'Groups to which the user belongs obtained', 'model':schemas.ReadGroup},
            500:{'description':'Internal error', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("60/minute")
async def get_groups_in_user(
        request: Request,
        limit:int = 10,
        skip: int = 0,
        user:User = Depends(auth_user),
        group_service: GroupService = Depends(get_group_service)) -> List[schemas.ReadGroup]:

    try:
        return await group_service.get_groups_where_user_in(user.user_id, limit, skip)

    except SQLAlchemyError as e:
        logger.error(f'[get_groups_in_user] Database Error:  {str(e)}')
        raise exceptions.DatabaseError(error=e, func='get_groups')
    except Exception as e:
        logger.error(f'[get_groups_in_user] Unexpected Error:  {str(e)}')
        raise

@router.post(
        '/{group_id}/{user_id}',
        description='Allows an authenticated user with Administrator or Editor rol to append a new user to group.',
        responses={
                201:{'description':'User added to group', 'model':responses.GroupAppendUserSucces},
                400:{'description':'request error', 'model':responses.ErrorInRequest},
                401:{'description':'User not authorized', 'model':responses.NotAuthorized},
                404:{'description':'Group not found', 'model':responses.NotFound},
                500:{'description':'Internal error', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("20/minute")
async def append_user_group(
        request: Request,
        group_id: int,
        user_id: int,
        auth_data: dict = Depends(require_role(roles=['admin', 'editor'])),
        group_service: GroupService = Depends(get_group_service)):

    try:
        actual_role = auth_data['role']
        actual_user = auth_data['user']

        return await group_service.append_user(group_id, user_id, actual_user.user_id)

    except SQLAlchemyError as e:
        logger.error(f'[append_user_group] Database Error:  {str(e)}')
        raise exceptions.DatabaseError(error=e, func='get_groups')
    except Exception as e:
        logger.error(f'[append_user_group] Unexpected Error:  {str(e)}')
        raise

@router.delete(
        '/{group_id}/{user_id}',
        description='Allows an authenticated user with Administrator or Editor role to remove a user from a group.',
        responses={
                200:{'description':'User removed from the group', 'model':responses.GroupDeleteUserSucces},
                400:{'description':'request error', 'model':responses.ErrorInRequest},
                401:{'description':'User not authorized', 'model':responses.NotAuthorized},
                404:{'description':'Group not found', 'model':responses.NotFound},
                500:{'description':'Internal error', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("5/minute")
async def delete_user_group(  
        request: Request,
        group_id: int,
        user_id: int,
        auth_data: dict = Depends(require_role(roles=['admin', 'editor'])),
        group_service: GroupService = Depends(get_group_service)):

    try:
        actual_role = auth_data['role']
        actual_user: User = auth_data['user']

        return await group_service.delete_user(
            group_id=group_id,
            user_id=user_id,
            actual_user_id=actual_user.user_id,
            actual_user_role=actual_role
        )
    except SQLAlchemyError as e:
        logger.error(f'[delete_user_group] Database Error:  {str(e)}')
        raise exceptions.DatabaseError(error=e, func='get_groups')
    except Exception as e:
        logger.error(f'[delete_user_group] Unexpected Error:  {str(e)}')
        raise

@router.patch(
        '/{group_id}/{user_id}',
        description='Permite al usuario autenticado con rol Administrador el modificar el rol de un usuario en el grupo',
        responses={
            200:{'description':'Usuario actualizado en el Grupo', 'model':responses.GroupUPdateUserSucces},
            400:{'description':'request error', 'model':responses.ErrorInRequest},
            401:{'description':'Usuario no autorizado', 'model':responses.NotAuthorized},
            404:{'description':'Grupo no encontrado', 'model':responses.NotFound},
            500:{'description':'error interno', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("10/minute")
async def update_user_group(
        request: Request,
        group_id: int,
        user_id: int,
        update_role: schemas.UpdateRoleUser,
        auth_data: dict = Depends(require_role(roles=['admin'])),
        group_service: GroupService = Depends(get_group_service)):

    try:
        actual_user = auth_data['user']

        return await group_service.update_user_role(
            group_id,
            user_id,
            update_role.role,
            actual_user.user_id
        )

    except RecursionError as e:
        raise 
    except SQLAlchemyError as e:
        logger.error(f'[update_user_group] Database Error:  {str(e)}')
        raise exceptions.DatabaseError(error=e, func='get_groups')
    except Exception as e:
        logger.error(f'[update_user_group] Unexpected Error:  {str(e)}')
        raise

@router.get(
        '/{group_id}/users',
        description=""" Obtained all the users of the group.
                        'skip' receives an "int" that skips the result obtained.
                        'limit' receives an "int" that limits the result obtained.""",
        responses={
                200:{'description':'Usuarios del Grupo obtenidos', 'model':schemas.ReadGroupUser},
                404:{'description':'Grupo no encontrado', 'model':responses.NotFound},
                500:{'description':'error interno', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("60/minute")
async def get_user_in_group(
        request: Request, 
        group_id: int,
        limit:int = 10,
        skip: int = 0,
        user: User = Depends(auth_user),
        group_service: GroupService = Depends(get_group_service)) -> List[schemas.ReadGroupUser]:

    try:
        return await group_service.get_users_in_group(group_id, limit, skip)

    except SQLAlchemyError as e:
        logger.error(f'[get_user_in_group] Database Error:  {str(e)}')
        raise exceptions.DatabaseError(error=e, func='get_groups')
    except Exception as e:
        logger.error(f'[get_user_in_group] Unexpected Error:  {str(e)}')
        raise
