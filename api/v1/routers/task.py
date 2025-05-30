from fastapi import APIRouter, Depends, Request
from models import db_models, schemas, exceptions, responses
from .auth import auth_user
from db.database import get_session, Session, select, SQLAlchemyError, joinedload, redis_client, redis
from typing import List
from core.utils import found_task_or_404, get_user_or_404, found_user_in_project_or_404
from core.permission import require_permission
from core.logger import logger
from core.limiter import limiter
from core.event_ws import format_notification
from .ws import manager
import json

router = APIRouter(prefix='/task', tags=['Task'])

@router.get(
        '',
        description=""" Obtain all of assigned tasks this user.
                    'skip' receives an "int" that skips the result obtained.
                    'limit' receives an "int" that limits the result obtained""",
        responses={ 200: {'description':'Tasks obtained', 'model':schemas.ReadTask},
                    500: {'description':'Internal error', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("30/minute")
async def get_task(
        request:Request,
        limit:int = 10,
        skip: int = 0,
        user:db_models.User = Depends(auth_user),
        session:Session = Depends(get_session)) -> List[schemas.ReadTask]:

    try:
        key = f'task:user:user_id:{user.user_id}:limit:{limit}:offset:{skip}'
        cached = await redis_client.get(key)

        if cached:
            decoded = json.loads(cached)
            logger.info(f'[get_task] Redis Cache Hit - Key: {key}')
            return decoded

        stmt = (select(db_models.Task)
                    .join(db_models.tasks_user, db_models.Task.task_id == db_models.tasks_user.task_id)
                    .where(db_models.tasks_user.user_id == user.user_id)
                    .limit(limit).offset(skip))

        found_tasks = session.exec(stmt).all()

        to_cache = [
            schemas.ReadTask(
                task_id=task.task_id,
                project_id=task.project_id,
                description=task.description,
                date_exp=task.date_exp,
                state=task.state
            )
            for task in found_tasks
        ]

        try:
            await redis_client.setex(key, 10, json.dumps([task.model_dump() for task in to_cache], default=str))
            logger.info(f'[get_task] Redis Cache Set - Key: {key}')
        except redis.RedisError as e:
            logger.warning(f'[get_task] Redis Cache Set Error | Error: {str(e)}')

        return to_cache

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
        session: Session = Depends(get_session)) -> List[schemas.ReadUser]:

    try:
        key = f'task:users:task_id:{task_id}:limit:{limit}:offset:{skip}'
        cached = await redis_client.get(key)

        if cached:
            decoded = json.loads(cached)
            logger.info(f'[get_users_for_task] Redis Cache Hit - Key: {key}')
            return decoded
        
        stmtm = (select(db_models.User.user_id, db_models.User.username)
                    .join(db_models.tasks_user, db_models.tasks_user.user_id == db_models.User.user_id)
                    .where(db_models.tasks_user.task_id == task_id)
                    .limit(limit).offset(skip))

        resultados = session.exec(stmtm).all()

        to_cache = [
            schemas.ReadUser(user_id=user_id, username=username)
            for user_id, username in resultados
            ]

        # Guarda la respuesta
        try:
            await redis_client.setex(key, 600, json.dumps([user_.model_dump() for user_ in to_cache], default=str))
            logger.info(f'[get_users_for_task] Redis Cache Set - Key: {key}')
        except redis.RedisError as e:
            logger.warning(f'[get_users_for_task] Redis Cache Set Error | Error: {str(e)}')

        return to_cache

    except SQLAlchemyError as e:
        logger.error(f'[get_users_for_task] Database Error | Error: {str(e)}')
        raise exceptions.DatabaseError(error=e, func='get_users_for_task')

@router.get(
        '/{project_id}',
        description= """ Obtain all assigned proyect tasks.
                        'skip' receives an "int" that skips the result obtained.
                        'limit' receives an "int" that limits the result obtained.""",
        responses={ 200: {'description':'Tasks from project obtained', 'model':schemas.ReadTaskInProject},
                    500: {'description':'Internal error', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("15/minute")
async def get_task_in_project(
        request:Request,
        project_id: int,
        limit:int = 10,
        skip: int = 0,
        user: db_models.User = Depends(auth_user),
        session: Session = Depends(get_session)) -> List[schemas.ReadTaskInProject]:

    try:
        key = f'task:users:project_id:{project_id}:user_id:{user.user_id}:limit:{limit}:offset:{skip}'
        cached = await redis_client.get(key)

        if cached:
            decoded = json.loads(cached)
            logger.info(f'[get_task_in_project] Redis Cache Hit - Key: {key}')
            return decoded

        # Selecciona las tareas asignadas a los usuarios en el proyecto
        stmt = (select(db_models.Task)
                    .join(db_models.tasks_user, db_models.tasks_user.task_id == db_models.Task.task_id)
                    .join(db_models.project_user, db_models.project_user.user_id == db_models.tasks_user.user_id)
                    .where(db_models.project_user.project_id == project_id, db_models.project_user.user_id == user.user_id)
                    .options(joinedload(db_models.Task.asigned))
                    .limit(limit).offset(skip))
        
        found_tasks = session.exec(stmt).unique().all()

        to_cache = [
            schemas.ReadTaskInProject(
                task_id=task.task_id,
                description=task.description,
                date_exp=task.date_exp,
                state=task.state,
                asigned=task.asigned
            )
            for task in found_tasks
        ]

        # Guarda la respuesta
        try:
            await redis_client.setex(key, 10, json.dumps([task_.model_dump() for task_ in to_cache], default=str))
            logger.info(f'[get_task_in_project] Redis Cache Set - Key: {key}')
        except redis.RedisError as e:
            logger.warning(f'[get_task_in_project] Redis Cache Set Error | Error {str(e)}')

        return to_cache
    
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
        session: Session = Depends(get_session)):

    try:
        # Busca el usuario al que va a asignarse la tarea, y si existe en el proyecto
        if new_task.user_ids:
            for user_id in new_task.user_ids:
                get_user_or_404(user_id=user_id, session=session)
                
                found_user_in_project_or_404(user_id=user_id, project_id=project_id, session=session)

        task = db_models.Task(
            project_id=project_id,
            description=new_task.description,
            date_exp=new_task.date_exp)

        session.add(task)
        session.commit()
        session.refresh(task)

        for user_id in new_task.user_ids:
            task_user = db_models.tasks_user(
                task_id=task.task_id,
                user_id=user_id)
            session.add(task_user)

            # Se crea la notificacion
            outgoing_event_json = format_notification(
                        notification_type='assigned_task',
                        message=f'Ya no estas asignado a task {task.task_id} en project {project_id}')

            # Envia el evento
            await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

        session.commit()

        return {'detail':'Se ha creado una nueva tarea y asignado los usuarios con exito'}
    
    except SQLAlchemyError as e:
        logger.error(f'[create_task] Database Error | Error: {str(e)}')
        session.rollback()
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
        session: Session = Depends(get_session)):

    try:
        actual_permission = auth_data['permission']
        user: db_models.User = auth_data['user']

        # Busca la task seleccionada
        task = found_task_or_404(project_id=project_id, task_id=task_id, session=session)

        if task.description != update_task.description and update_task.description:
            task.description = update_task.description

        if task.date_exp != update_task.date_exp and update_task.date_exp:
            task.date_exp = update_task.date_exp

        if task.state != update_task.state and update_task.state:
            task.state = update_task.state

        # Verifica si hay nuevos usuarios a agregar 
        if update_task.append_user_ids:
            if actual_permission == 'admin':
                for user_id in update_task.append_user_ids:
                    # Verifica que el usuario exista
                    user_exists = session.get(db_models.User, user_id)
                    if not user_exists:
                        logger.error(f'[update_task] User {user_id} not found')
                        raise exceptions.UserNotFoundError(user_id)

                    # Verifica que el usuario exista en el projecto
                    stmt = (select(db_models.project_user).where(
                        db_models.project_user.user_id == user_exists.user_id,
                        db_models.project_user.project_id == project_id))
                    
                    user_in_project = session.exec(stmt).first()
                    if not user_in_project:
                        logger.error(f'[update_task] User {user_id} not found in project {project_id}')
                        raise exceptions.UserNotInProjectError(project_id=project_id, user_id=user_id)

                    # Verifica que el usuario este asignado al task
                    stmt = (select(db_models.tasks_user).where(
                        db_models.tasks_user.user_id == user_exists.user_id,
                        db_models.tasks_user.task_id == task_id))
                    
                    user_in_task = session.exec(stmt).first()
                    if user_in_task:
                        logger.error(f'[update_task] User {user_id} was already assigned to task {task_id}')
                        raise exceptions.TaskIsAssignedError(user_id=user_id, task_id=task_id)

                    # Agrega el usuario al task
                    task_user = db_models.tasks_user(
                        task_id=task.task_id,
                        user_id=user_id)
                    session.add(task_user)
            else:
                logger.error(f'[update_task] Unauthorized | User {user.user_id} not authorized for this action')
                raise exceptions.NotAuthorized(user.user_id)

        # Verifica si hay usuarios para eliminar de la tarea 
        if update_task.exclude_user_ids:
            if actual_permission == 'admin':
                for user_id in update_task.exclude_user_ids:
                    # Verifica que el usuario este asignado al task
                    stmt = (select(db_models.tasks_user).where(
                        db_models.tasks_user.user_id == user_id,
                        db_models.tasks_user.task_id == task_id))
                    
                    user_in_task = session.exec(stmt).first()
                    if not user_in_task:
                        logger.error(f'[update_task] Update Task Error | User {user_id} not assigned to task {task_id}')
                        raise exceptions.TaskIsNotAssignedError(user_id=user_id, task_id=task_id)

                    session.delete(user_in_task)
            else:
                logger.error(f'[update_task] Unauthorized | User {user.user_id} not authorized for this action')
                raise exceptions.NotAuthorized(user.user_id)

        session.commit()

        task = session.get(db_models.Task, task_id)

        if update_task.append_user_ids:
            for user_id in update_task.append_user_ids:
                # Se crea la notificacion
                outgoing_event_json = format_notification(
                        notification_type='assigned_task',
                        message=f'Te asignaron a task {task_id} en project {project_id}')
                
                # Envia el evento
                await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

        if update_task.exclude_user_ids:
            for user_id in update_task.exclude_user_ids:
                # Se crea la notificacion
                outgoing_event_json = format_notification(
                        notification_type='assigned_task',
                        message=f'Ya no estas asignado a task {task_id} en project {project_id}')
                
                # Envia el evento
                await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

        try:
            await redis_client.delete(f'task:users:project_id:{project_id}:user_id:*:limit:*:offset:*')
            logger.info(f'[update_task] Redis Cache Delete Succes - Key: task:users:project_id:{project_id}:user_id:*:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'[update_task] Redis Cache Delete Error | Error: {str(e)}')

        return {'detail':'Se ha actualizado la tarea'}

    except SQLAlchemyError as e:
        logger.error(f'[update_task] Database Error | Error: {str(e)}')
        session.rollback()
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
        session: Session = Depends(get_session)):

    try:        
        # Verifica que exista la task
        task = found_task_or_404(project_id=project_id, task_id=task_id, session=session)

        session.delete(task)
        session.commit()

        try:
            await redis_client.delete(f'task:users:task_id:{task_id}:limit:*:offset:*')
            await redis_client.delete(f'task:users:project_id:{project_id}:user_id:*:limit:*:offset:*')

            logger.info(f'[delete_task] Redis Cache Delete Success - Key: task:users:task_id:{task_id}:limit:*:offset:*')
            logger.info(f'[delete_task] Redis Cache Delete Success - Key: task:users:project_id:{project_id}:user_id:*:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'[delete_task] Redis Cache Delete Error | Error: {str(e)}')

        return {'detail':'Se ha eliminado la tarea'}

    except SQLAlchemyError as e:
        logger.error(f'[delete_task] Database Error | Error: {str(e)}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='delete_task')