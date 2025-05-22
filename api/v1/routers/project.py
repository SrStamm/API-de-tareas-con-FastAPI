from fastapi import APIRouter, Depends, Request
from models import db_models, schemas, exceptions, responses
from db.database import get_session, Session, select, selectinload, SQLAlchemyError, redis_client, redis
from typing import List
from .auth import auth_user
from core.utils import get_group_or_404, get_user_or_404, found_project_or_404
from core.permission import require_permission, require_role
from core.logger import logger
from core.limiter import limiter
from .ws import manager
from datetime import datetime
import json

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
        session: Session = Depends(get_session)) -> List[schemas.ReadBasicProject]:

    try:
        key = f'project:user:user_id:{user.user_id}:limit:{limit}:offset:{skip}'
        # Busca si existe una respuesta cacheada
        cached = await redis_client.get(key)

        # Devuelve si es verdad
        if cached:
            logger.info(f'Redis Cache: {key}')
            decoded = json.loads(cached)
            return decoded

        stmt = (select(db_models.Project.project_id, db_models.Project.group_id, db_models.Project.title)
                    .where( db_models.Project.project_id == db_models.project_user.project_id,
                            db_models.project_user.user_id == user.user_id)
                    .limit(limit).offset(skip))

        found_projects = session.exec(stmt).all()

        # Cachea la respuesta
        to_cache = [
            schemas.ReadBasicProject(group_id=group_id, project_id=project_id, title=title)
            for group_id, project_id, title in found_projects
            ]

        # Guarda la respuesta
        try:
            await redis_client.setex(key, 6000, json.dumps([project_.model_dump() for project_ in to_cache], default=str))
        except redis.RedisError as e:
            logger.warning(f'Error al cachear en Redis: {e}')

        return to_cache

    except SQLAlchemyError as e:
        logger.error(f'Error al obtener los proyectos a los que pertenece el user {user.user_id}: {e}')
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
        session: Session = Depends(get_session)) -> List[schemas.ReadProject]:

    try:
        key = f'projects:group_id:{group_id}:limit:{limit}:offset:{skip}'
        # Busca si existe una respuesta cacheada
        cached = await redis_client.get(key)

        # Devuelve si es verdad
        if cached:
            logger.info(f'Redis Cache: {key}')
            decoded = json.loads(cached)
            return decoded
        
        get_group_or_404(group_id=group_id, session=session)

        stmt = (select(db_models.Project)
                    .options(selectinload(db_models.Project.users))
                    .where(db_models.Project.group_id == group_id)
                    .limit(limit).offset(skip))

        found_projects = session.exec(stmt).all()
        
        # Cachea la respuesta
        to_cache = [
            {
                **project.model_dump(),
                'users': [user.model_dump() for user in project.users]
            }
            for project in found_projects]

        # Guarda la respuesta
        await redis_client.setex(key, 6000, json.dumps(to_cache, default=str))

        return to_cache
    
    except SQLAlchemyError as e:
        logger.error(f'Error al obtener todos los proyectos del grupo {group_id}: {e}')
        raise exceptions.DatabaseError(error=e, func='get_projects')

@router.post(
        '/{group_id}',
        description= """Allows create an new proyect on the group to authenticated user.
                        To create it, you need an 'title', optional 'description'""",
        responses={
            200:{'description':'Project created', 'model':responses.ProjectCreateSucces},
            404:{'description':'Group not found','model':responses.NotFound},
            500:{'description':'Internal error','model':responses.DatabaseErrorResponse}})
@limiter.limit("10/minute")
async def create_project(
        request:Request,
        new_project: schemas.CreateProject,
        group_id: int,
        auth_data: dict = Depends(require_role(roles=['admin'])),
        session:Session = Depends(get_session)):
    try:
        actual_user = auth_data['user']

        found_group = get_group_or_404(group_id, session)

        project = db_models.Project(**new_project.model_dump(), group_id=found_group.group_id)

        session.add(project)
        session.commit()
        session.refresh(project)

        # Agregar al usuario creador al grupo con el rol de administrador
        project_user = db_models.project_user(
            project_id=project.project_id,
            user_id=actual_user.user_id,
            permission=db_models.Project_Permission.ADMIN
        )

        session.add(project_user)

        stmt = (select(db_models.group_user).where(db_models.group_user.group_id == group_id))
        users_in_group = session.exec(stmt).all()

        if users_in_group:
            add_user_ids = [actual_user.user_id]
            for group_user in users_in_group:
                if group_user.role == 'admin' and group_user.user_id not in add_user_ids:
                    project_user = db_models.project_user(
                        project_id=project.project_id,
                        user_id=group_user.user_id,
                        permission='admin')

                    session.add(project_user)
                    add_user_ids.append(group_user.user_id)

        session.commit()

        try:
            await redis_client.delete('projects:group_id:{group_id}:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'Error al cachear en Redis {e}')

        return {'detail':'Se ha creado un nuevo proyecto de forma exitosa'}

    except SQLAlchemyError as e:
        logger.error(f'Error al crear un proyecto en el grupo {group_id}: {e}')
        session.rollback()
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
        session: Session = Depends(get_session)):  

    try:
        found_project = found_project_or_404(group_id=group_id, project_id=project_id, session=session)

        if found_project.title != updated_project.title and updated_project.title is not None:
            found_project.title = updated_project.title

        if found_project.description != updated_project.description and updated_project.description is not None:
            found_project.description = updated_project.description

        session.commit()
        session.refresh(found_project)

        try:
            await redis_client.delete('projects:group_id:{group_id}:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'Error al cachear en Redis {e}')

        return {'detail':'Se ha actualizado la informacion del projecto'}
    
    except SQLAlchemyError as e:
        logger.error(f'Error al actualizar el proyecto {project_id} en el grupo {group_id}: {e}')
        session.rollback()
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
        session: Session = Depends(get_session)):

    try:
        # found_project = found_project_or_404(group_id=group_id, project_id=project_id, session=session)
        found_project = session.get(db_models.Project, project_id)
        session.delete(found_project)
        session.commit()

        # Elimina cache
        try:
            await redis_client.delete('projects:group_id:{group_id}:limit:*:offset:*')
            await redis_client.delete('project:users:group_id:{group_id}:project_id:{project_id}:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'Error al eliminar cache de Redis {e}')

        return {'detail':'Se ha eliminado el proyecto'}

    except SQLAlchemyError as e:
        logger.error(f'Error al eliminar el proyecto {project_id} en el grupo {group_id}: {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='delete_project')

@router.post(
        '/{group_id}/{project_id}/{user_id}',
        description= """Allows an authenticated user with Administrator permissions
                        to add a new user to the proyect if it exists in the group.""",
        responses={
            200:{'description':'User added to project', 'model':responses.ProjectAppendUserSucces},
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
        session: Session = Depends(get_session)):

    try:
        found_project = found_project_or_404(group_id, project_id, session)

        # Busca el usuario
        user = get_user_or_404(user_id=user_id, session=session) 

        # Busca el grupo y verifica si el usuario existe en este
        group = get_group_or_404(group_id=group_id, session=session)

        if not user in group.users:
            logger.error(f'El user {user_id} no existe en el grupo {group_id}')
            raise exceptions.UserNotInGroupError(user_id=user_id, group_id=group_id)

        if user in found_project.users:
            logger.error(f'El user {user_id} ya existe en el proyecto {project_id}')
            raise exceptions.UserInProjectError(user_id=user_id, project_id=project_id)

        # Lo agrega al grupo
        found_project.users.append(user)

        session.commit()

        # Se crea la notificacion
        outgoing_payload = schemas.OutgoingNotificationPayload(
            notification_type='add_user_to_project',
            message=f'Fuiste agregagdo al project {project_id}',
            timestamp=datetime.now())

        # Crea el evento
        outgoing_event = schemas.WebSocketEvent(
            type='notification',
            payload=outgoing_payload.model_dump()
        )

        # Parsea el evento
        outgoing_event_json = outgoing_event.model_dump_json()

        # Envia el evento
        await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

        # Elimina cache
        try:
            await redis_client.delete('project:users:group_id:{group_id}:project_id:{project_id}:limit:*:offset:*')
            await redis_client.delete('projects:group_id:{group_id}:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'Error al eliminar cache en Redis {e}')

        return {'detail':'El usuario ha sido agregado al proyecto'}
    
    except SQLAlchemyError as e:
        logger.error(f'Error al agregar al user {user_id} al proyecto {project_id}: {e}')
        session.rollback()
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
        session: Session = Depends(get_session)):

    try:
        found_project = found_project_or_404(group_id, project_id, session)
        
        # Busca el usuario
        user = get_user_or_404(user_id=user_id, session=session)

        # Busca el grupo y verifica si el usuario existe en este
        group = get_group_or_404(group_id=group_id, session=session)
        
        if not user in group.users:
            logger.error(f'El user {user_id} no existe en el grupo {group_id}')
            raise exceptions.UserNotInGroupError(user_id=user_id, group_id=group_id)

        if user in found_project.users:
            # Lo elimina del proyecto
            found_project.users.remove(user)
            session.commit()

            # Se crea la notificacion
            outgoing_payload = schemas.OutgoingNotificationPayload(
                notification_type='delete_user_from_project',
                message=f'Fuiste eliminado del project {project_id}',
                timestamp=datetime.now())

            # Crea el evento
            outgoing_event = schemas.WebSocketEvent(
                type='notification',
                payload=outgoing_payload.model_dump()
            )

            # Parsea el evento
            outgoing_event_json = outgoing_event.model_dump_json()

            # Envia el evento
            await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

            # Elimina cache
            try:
                await redis_client.delete('project:users:group_id:{group_id}:project_id:{project_id}:limit:*:offset:*')
                await redis_client.delete('projects:group_id:{group_id}:limit:*:offset:*')
            except redis.RedisError as e:
                logger.warning(f'Error al eliminar cache en Redis {e}')

            return {'detail':'El usuario ha sido eliminado del proyecto'}
        else:
            logger.error(f'El user {user_id} no existe en el proyecto {project_id}')
            raise exceptions.UserNotInProjectError(user_id=user_id, project_id=project_id)
    
    except SQLAlchemyError as e:
        logger.error(f'Error al remover al user {user_id} del proyecto {project_id}: {e}')
        session.rollback()
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
        session: Session = Depends(get_session)):

    try:
        project = found_project_or_404(group_id, project_id, session)

        # Busca el usuario
        stmt = (select(db_models.project_user)
                    .where(db_models.project_user.user_id == user_id, db_models.project_user.project_id == project.project_id))

        user = session.exec(stmt).first()

        if not user:
            logger.error(f'El user {user_id} no existe en el proyecto {project_id}')
            raise exceptions.UserNotInProjectError(project_id=project_id, user_id=user_id)

        user.permission = update_role.permission

        session.commit()
        session.refresh(user)

        # Se crea la notificacion
        outgoing_payload = schemas.OutgoingNotificationPayload(
            notification_type='permission_update',
            message=f'Tus permisos en project {project_id} fue actualizado a {user.permission.value}',
            timestamp=datetime.now())

        # Crea el evento
        outgoing_event = schemas.WebSocketEvent(
            type='notification',
            payload=outgoing_payload.model_dump()
        )

        # Parsea el evento
        outgoing_event_json = outgoing_event.model_dump_json()

        # Envia el evento
        await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

        # Elimina cache
        try:
            await redis_client.delete('project:users:group_id:{group_id}:project_id:{project_id}:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'Error al eliminar cache en Redis {e}')
        return {'detail':'Se ha cambiado los permisos del usuario en el proyecto'}

    except SQLAlchemyError as e:
        logger.error(f'Error al actualizar permisos del user {user_id} del proyecto {project_id}: {e}')
        session.rollback()
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
        session:Session = Depends(get_session),
        user: db_models.User = Depends(auth_user)) -> List[schemas.ReadProjectUser]:

    try:
        key = f'project:users:group_id:{group_id}:project_id:{project_id}:limit:{limit}:offset:{skip}'
        cached = await redis_client.get(key)

        if cached:
            logger.info(f'Redis Cache: {key}')
            decoded = json.loads(cached)
            return decoded

        found_project_or_404(group_id, project_id, session)

        stmt = (select(db_models.User.user_id, db_models.User.username, db_models.project_user.permission)
                    .join(db_models.project_user, db_models.project_user.user_id == db_models.User.user_id)
                    .where(db_models.project_user.project_id == project_id)
                    .limit(limit).offset(skip))

        results = session.exec(stmt).all()

        if not results:
            logger.error(f'No se encontraron los usuarios en el proyecto {project_id}')
            raise exceptions.UsersNotFoundInProjectError(project_id=project_id)

        # El resultado son tuplas, entonces se debe hacer lo siguiente para que devuelva la informacion solicitada
        to_cache = [
            schemas.ReadProjectUser(user_id=user_id, username=username, permission=permission)
            for user_id, username, permission in results
        ]

        try:
            await redis_client.setex(key, 600, json.dumps([project.model_dump() for project in to_cache], default=str))
        except redis.RedisError as e:
            logger.warning(f'Error al cachear en Redis {e}')

        return to_cache

    except SQLAlchemyError as e:
        logger.error(f'Error al obtener los usuarios del proyecto {project_id}: {e}')
        raise exceptions.DatabaseError(error=e, func='get_user_in_project')