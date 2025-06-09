from fastapi import APIRouter, Depends, Request
from models import db_models, schemas, exceptions, responses
from models.db_models import User
from db.database import SQLAlchemyError, redis_client, redis
from typing import List
from .auth import auth_user
from core.permission import require_permission, require_role
from core.logger import logger
from core.limiter import limiter


from dependency.project_dependencies import get_project_service, ProjectService

router = APIRouter(prefix='/project', tags=['Project'])

@router.get(
        '/me',
        description="""  Obtained all projects where user is part.
                    'skip' receives an "int" that skips the result obtained.
                    'limit' receives an "int" that limits the result obtained.""",
        responses={
            200:{'description':'Projects where user is part obtained', 'model':schemas.ReadBasicProject},
            500:{'description':'Internal error','model':responses.DatabaseErrorResponse}})
@limiter.limit("10/minute")
async def get_projects_iam(
        request:Request,
        limit:int = 10,
        skip: int = 0,
        user: db_models.User = Depends(auth_user),
        project_serv: ProjectService = Depends(get_project_service)) -> List[schemas.ReadBasicProject]:

    try:
        return await project_serv.get_projects_iam(user.user_id, limit, skip)

    except SQLAlchemyError as e:
        logger.error(f'[get_projects_iam] Database Error for user {user.user_id} | Error: {e}')
        raise exceptions.DatabaseError(error=e, func='get_projects_iam')

@router.get(
        '/{group_id}',
        description=""" Obtained all of projects of the group.
                        'skip' receives an "int" that skips the result obtained.
                        'limit' receives an "int" that limits the result obtained.""",
        responses={
            200:{'description':'Projects of the group obtained', 'model':schemas.ReadProject},
            404:{'description':'Group or proyects not found','model':responses.NotFound},
            500:{'description':'Internal error','model':responses.DatabaseErrorResponse}})
@limiter.limit("20/minute")
async def get_projects(
        request:Request,
        group_id: int,
        limit:int = 10,
        skip: int = 0,
        auth_data: dict = Depends(require_role(roles=['admin'])),
        project_serv: ProjectService = Depends(get_project_service)) -> List[schemas.ReadProject]:

    try:
        return await project_serv.get_all_projects(group_id, limit, skip)
    
    except SQLAlchemyError as e:
        logger.error(f'[get_projects] Database Error Group:{group_id} | Error: {str(e)}')
        raise exceptions.DatabaseError(error=e, func='get_projects')

@router.post(
        '/{group_id}',
        description= """Allows create an new proyect on the group to authenticated user.
                        To create it, you need an 'title', optional 'description'""",
        responses={
            201:{'description':'Project created', 'model':responses.ProjectCreateSucces},
            404:{'description':'Group not found','model':responses.NotFound},
            500:{'description':'Internal error','model':responses.DatabaseErrorResponse}})
@limiter.limit("10/minute")
async def create_project(
        request:Request,
        new_project: schemas.CreateProject,
        group_id: int,
        auth_data: dict = Depends(require_role(roles=['admin'])),
        project_serv: ProjectService = Depends(get_project_service)):
    try:
        actual_user: User = auth_data['user']

        return await project_serv.create_project(
            group_id,
            actual_user.user_id,
            new_project
        )

    except SQLAlchemyError as e:
        logger.error(f'Error al crear un proyecto en el grupo {group_id}: {e}')
        raise exceptions.DatabaseError(error=e, func='create_project')

@router.patch(
        '/{group_id}/{project_id}',
        description= """Allows update an proyect of the grupo if user has Administrator permissions on the proyect.
                        Allows modificate 'title' and 'description' """,
        responses={
            200:{'description':'Project updated', 'model':responses.ProjectUpdateSucces},
            401:{'description':'User not authorized','model':responses.NotAuthorized},
            404:{'description':'Group or project not found','model':responses.NotFound},
            500:{'description':'Internal error','model':responses.DatabaseErrorResponse}})
@limiter.limit("15/minute")
async def update_project(
        request:Request,
        group_id: int,
        project_id: int,
        updated_project: schemas.UpdateProject,
        auth_data: dict = Depends(require_permission(permissions=['admin', 'write'])),
        project_serv: ProjectService = Depends(get_project_service)):  
    try:
        return await project_serv.update_project(
            group_id,
            project_id,
            updated_project
        )    
    except SQLAlchemyError as e:
        logger.error(f'[update_project] Database Error | Error: {e}')
        raise exceptions.DatabaseError(error=e, func='update_project')

@router.delete(
        '/{group_id}/{project_id}',
        description="""Allows remove an project of the group if an authenticated user has Administrator permissions on the proyect""",
        responses={
            200:{'description':'Proyect deleted', 'model':responses.ProjectDeleteSucces},
            401:{'description':'User not authorized','model':responses.NotAuthorized},
            404:{'description':'Group or project not found','model':responses.NotFound},
            500:{'description':'Internal error','model':responses.DatabaseErrorResponse}})
@limiter.limit("5/minute")
async def delete_project(
        request:Request,
        group_id: int,
        project_id: int,
        auth_data: dict = Depends(require_permission(permissions=['admin'])),
        project_serv: ProjectService = Depends(get_project_service)):

    try:
        return await project_serv.delete_project( group_id, project_id )

    except SQLAlchemyError as e:
        logger.error(f'[delete_project] Database Error | Error: {str(e)}')
        raise exceptions.DatabaseError(error=e, func='delete_project')

@router.post(
        '/{group_id}/{project_id}/{user_id}',
        description= """Allows an authenticated user with Administrator permissions
                        to add a new user to the proyect if it exists in the group.""",
        responses={
            201:{'description':'User added to project', 'model':responses.ProjectAppendUserSucces},
            400:{'description':'Error in request', 'model':responses.ErrorInRequest},
            401:{'description':'User not authorized','model':responses.NotAuthorized},
            404:{'description':'Group or project not found','model':responses.NotFound},
            500:{'description':'Internal error','model':responses.DatabaseErrorResponse}})
@limiter.limit("10/minute")
async def add_user_to_project(
        request:Request,
        group_id: int,
        user_id: int,
        project_id: int,
        auth_data: dict = Depends(require_permission(permissions=['admin'])),
        project_serv: ProjectService = Depends(get_project_service)):

    try:
        return await project_serv.add_user(
            group_id,
            project_id,
            user_id
        )
    
    except SQLAlchemyError as e:
        logger.error(f'[add_user_to_project] Database Error | Error: {str(e)}')
        raise exceptions.DatabaseError(error=e, func='add_user_to_project')

@router.delete(
        '/{group_id}/{project_id}/{user_id}',
        description="""Allow an authenticated user with Administrator permission
                        to remove an user of the proyect""",
        responses={
            200:{'description':'User removed of the project', 'model':responses.ProjectDeleteUserSucces},
            400:{'description':'Error in request', 'model':responses.ErrorInRequest},
            401:{'description':'User not authenticated','model':responses.NotAuthorized},
            404:{'description':'Group or project not found','model':responses.NotFound},
            500:{'description':'Internal error','model':responses.DatabaseErrorResponse}})
@limiter.limit("10/minute")
async def remove_user_from_project(
        request:Request,
        group_id: int,
        project_id: int,
        user_id: int,
        auth_data: dict = Depends(require_permission(permissions=['admin'])),
        project_serv: ProjectService = Depends(get_project_service)):

    try:
        return await project_serv.remove_user( group_id, project_id, user_id )

    except SQLAlchemyError as e:
        logger.error(f'[remove_user_from_project] Database Error | Error: {str(e)}')
        raise exceptions.DatabaseError(error=e, func='remove_user_from_project')

@router.patch(
        '/{group_id}/{project_id}/{user_id}',
        description= """Allow an authenticated user whit Administrator permission
                        to update a user's permission on a project""",
        responses={
            200:{'description':"User's permission on a project updated", 'model':responses.ProjectUPdateUserSucces},
            400:{'description':'Error in request', 'model':responses.ErrorInRequest},
            401:{'description':'User not authorized','model':responses.NotAuthorized},
            404:{'description':'Group or porject not found','model':responses.NotFound},
            500:{'description':'Internal error','model':responses.DatabaseErrorResponse}})
@limiter.limit("15/minute")
async def update_user_permission_in_project(
        request:Request,
        group_id: int,
        user_id: int,
        project_id: int,
        update_role: schemas.UpdatePermissionUser,
        auth_data: dict = Depends(require_permission(permissions=['admin'])),
        project_serv: ProjectService = Depends(get_project_service)):

    try:
        return await project_serv.update_user_permission_in_project(
            group_id, project_id, user_id, update_role
        )

    except SQLAlchemyError as e:
        logger.error(f'[update_user_permission_in_project] Database Error | Error: {str(e)}')
        raise exceptions.DatabaseError(error=e, func='update_user_permission_in_project')

@router.get(
        '/{group_id}/{project_id}/users',
        description=""" Obtained all users of the project.
                    'skip' receives an "int" that skips the result obtained.
                    'limit' receives an "int" that limits the result obtained.""",
        responses={
                200:{'description':'Users from the project obtained', 'model':schemas.ReadProjectUser},
                400:{'description':'Error in request', 'model':responses.ErrorInRequest},
                404:{'description':'Group or project not obtained','model':responses.NotFound},
                500:{'description':'Internal error','model':responses.DatabaseErrorResponse}})
@limiter.limit("20/minute")
async def get_user_in_project(
        request:Request,
        group_id: int,
        project_id: int,
        limit:int = 10,
        skip: int = 0,
        user: db_models.User = Depends(auth_user),
        project_serv: ProjectService = Depends(get_project_service)
        ) -> List[schemas.ReadProjectUser]:
    try:
        return await project_serv.get_user_in_project( group_id, project_id, limit, skip )

    except SQLAlchemyError as e:
        logger.error(f'[get_user_in_project] Database Error | Error: {str(e)}')
        raise exceptions.DatabaseError(error=e, func='get_user_in_project')