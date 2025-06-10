from fastapi import APIRouter, Depends, Request, Query
from models import db_models, schemas, exceptions, responses
from .auth import auth_user
from db.database import SQLAlchemyError
from typing import List
from core.permission import require_permission
from core.logger import logger
from core.limiter import limiter

from dependency.task_dependencies import get_task_service, TaskService

router = APIRouter(prefix='/task', tags=['Task'])

@router.get(
        '',
        description=""" Obtain all of assigned tasks this user.
                    'skip' receives an "int" that skips the result obtained.
                    'limit' receives an "int" that limits the result obtained.
                    'labels' receives a list with labels to filter the task.
                    'state' receives a list with states to filter the task.""",
        responses={ 200: {'description':'Tasks obtained', 'model':schemas.ReadTask},
                    500: {'description':'Internal error', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("30/minute")
async def get_task(
        request:Request,
        limit:int = 10,
        skip: int = 0,
        labels: List[db_models.TypeOfLabel] = Query(default=None),
        state: List[db_models.State] = Query(default=None),
        user:db_models.User = Depends(auth_user),
        task_serv: TaskService = Depends(get_task_service)) -> List[schemas.ReadTask]:

    try:
        return await task_serv.get_all_task_for_user(user.user_id, limit, skip, labels, state)

    except SQLAlchemyError as e:
        logger.error(f'[get_task] Database Error | Error: {str(e)}')
        raise exceptions.DatabaseError(error=e, func='get_task')

@router.get(
        '/{task_id}/users',
        description= """ Obtain all of asigned users to task.
                        'skip' receives an "int" that skips the result obtained.
                        'limit' receives an "int" that limits the result obtained.""",
        responses={ 200: {'description':'Users assigned to tasks obtained', 'model':schemas.ReadUser},
                    500: {'description':'Internal error', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("20/minute")
async def get_users_for_task(
        request:Request,
        task_id: int,
        limit:int = 10,
        skip: int = 0,
        user: db_models.User = Depends(auth_user),
        task_serv: TaskService = Depends(get_task_service)) -> List[schemas.ReadUser]:

    try:
        return await task_serv.get_users_for_task(task_id, limit, skip)

    except SQLAlchemyError as e:
        logger.error(f'[get_users_for_task] Database Error | Error: {str(e)}')
        raise exceptions.DatabaseError(error=e, func='get_users_for_task')

@router.get(
        '/{project_id}',
        description= """ Obtain all assigned proyect tasks.
                        'skip' receives an "int" that skips the result obtained.
                        'limit' receives an "int" that limits the result obtained.
                        'labels' receives a list with labels to filter the task.
                        'state' receives a list with states to filter the task.""",
        responses={ 200: {'description':'Tasks from project obtained', 'model':schemas.ReadTaskInProject},
                    500: {'description':'Internal error', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("15/minute")
async def get_task_in_project(
        request:Request,
        project_id: int,
        limit:int = 10,
        skip: int = 0,
        labels: List[db_models.TypeOfLabel] = Query(default=None),
        state: List[db_models.State] = Query(default=None),
        user: db_models.User = Depends(auth_user),
        task_serv: TaskService = Depends(get_task_service)) -> List[schemas.ReadTaskInProject]:

    try:
        return await task_serv.get_all_task_for_project(user.user_id, project_id, limit, skip, labels, state)
    
    except SQLAlchemyError as e:
        logger.error(f'[get_task_in_project] Database Error | Error: {str(e)}')
        raise exceptions.DatabaseError(error=e, func='get_task_in_project')

@router.post(
        '/{project_id}',
        description='Create a new task from the proyect',
        responses={
            201: {'description':'Task created', 'model':responses.TaskCreateSucces},
            404: {'description':'Data not found', 'model':responses.DataNotFound},
            500: {'description':'Internal error', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("10/minute")
async def create_task(
        request:Request,
        new_task: schemas.CreateTask,
        project_id: int,
        auth_data: dict = Depends(require_permission(permissions=['admin'])),
        task_serv: TaskService = Depends(get_task_service)):

    try:
        return await task_serv.create(new_task, project_id)
    
    except SQLAlchemyError as e:
        logger.error(f'[create_task] Database Error | Error: {str(e)}')
        raise exceptions.DatabaseError(error=e, func='create_task')

@router.patch(
        '/{project_id}/{task_id}', description='Update a specific task from the proyect',
        responses={ 200: {'description':'Task updated', 'model':responses.TaskUpdateSucces},
                    400: {'description':'Error in request', 'model':responses.ErrorInRequest},
                    401: {'description':'Unauthorized', 'model':responses.NotAuthorized},
                    404: {'description':'Data not foun', 'model':responses.DataNotFound},
                    500: {'description':'internal error', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("10/minute")
async def update_task(
        request:Request,
        task_id: int,
        project_id: int,
        update_task: schemas.UpdateTask,
        auth_data: dict = Depends(require_permission(permissions=['admin', 'write'])),
        task_serv: TaskService = Depends(get_task_service)):

    try:
        actual_permission = auth_data['permission']
        user: db_models.User = auth_data['user']

        return await task_serv.update_task(task_id, project_id, update_task, user, actual_permission)

    except SQLAlchemyError as e:
        logger.error(f'[update_task] Database Error | Error: {str(e)}')
        raise exceptions.DatabaseError(error=e, func='update_task')

@router.delete(
        '/{project_id}/{task_id}',
        description='Removes a specific task from a project',
        responses={ 200: {'description':'Task removed', 'model':responses.TaskDeleteSucces},
                    400: {'description':'Error in request', 'model':responses.ErrorInRequest},
                    500: {'description':'Internal error', 'model':responses.DatabaseErrorResponse}})
async def delete_task(
        task_id: int,
        project_id: int,
        auth_data: dict = Depends(require_permission(permissions=['admin'])),
        task_serv: TaskService = Depends(get_task_service)):

    try:        
        return await task_serv.delete(task_id, project_id)

    except SQLAlchemyError as e:
        logger.error(f'[delete_task] Database Error | Error: {str(e)}')
        raise exceptions.DatabaseError(error=e, func='delete_task')