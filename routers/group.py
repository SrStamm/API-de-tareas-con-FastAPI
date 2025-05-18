from fastapi import APIRouter, Depends, Request
from models import db_models, schemas, exceptions, responses
from db.database import get_session, Session, select, selectinload, SQLAlchemyError, redis_client, get_async_session, AsyncSession, redis
from typing import List
from .auth import auth_user
from core.utils import get_group_or_404, get_user_or_404, require_role, role_of_user_in_group
from core.logger import logger
from core.limiter import limiter
from routers.ws import manager
from datetime import datetime
import json

router = APIRouter(prefix='/group', tags=['Group'])

@router.get(
        '',
        description=""" Obtiene todos los grupos con informacion limitada.
                        'skip' recibe un int que saltea el resultado obtenido.
                        'limit' recibe un int para limitar los resultados obtenidos.""",
        responses={
            200:{'description':'Grupos obtenidos', 'model':schemas.ReadBasicDataGroup},
            500:{'description':'error interno', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("60/minute")
async def get_groups(
        request: Request,
        limit:int = 10,
        skip: int = 0,
        session: AsyncSession = Depends(get_async_session)) -> List[schemas.ReadBasicDataGroup]:

    try:
        key = f'groups:limit:{limit}:offset:{skip}'
        # Busca si existe una respuesta guardada y la busca
        cached = await redis_client.get(key)

        if cached:
            logger.info(f'Redis Cache: {key}')
            decoded = json.loads(cached)
            return decoded

        statement = (select(db_models.Group)
                    .options(selectinload(db_models.Group.users))
                    .order_by(db_models.Group.group_id).limit(limit).offset(skip))

        result = await session.exec(statement)

        found_group = result.all()

        # Cachea la respuesta
        to_cache = [
            {
                **group.model_dump(),
                'users': [user.model_dump() for user in group.users]
            }
            for group in found_group]

        # Guarda la respuesta
        try:
            await redis_client.setex(key, 300, json.dumps(to_cache, default=str))
        except redis.RedisError as e:
            logger.warning(f'Error al cachear en Redis: {e}')

        return to_cache

    except SQLAlchemyError as e:
        logger.error(f'Error al obtener los grupos {e}')
        raise exceptions.DatabaseError(error=e, func='get_groups')

@router.post(
        '',
        description=""" El usuario autenticado crea un nuevo grupo, necesita un 'name', y opcional 'description'.
                        El usuario se agrega de forma automatica como Administrador""",
        responses={
            200:{'description':'Grupo creado', 'model':responses.GroupCreateSucces},
            500:{'description':'error interno', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("15/minute")
async def create_group(
        request: Request,
        new_group: schemas.CreateGroup,
        user: db_models.User = Depends(auth_user),
        session: AsyncSession = Depends(get_async_session)):
    try:
        # Crear el grupo con el usuario creador
        group = db_models.Group(**new_group.model_dump())
        session.add(group)
        await session.commit()
        await session.refresh(group)

        # Agregar al usuario creador al grupo con el rol de administrador
        group_user = db_models.group_user(
            group_id=group.group_id,
            user_id=user.user_id,
            role=db_models.Group_Role.ADMIN
        )
        session.add(group_user)
        await session.commit()

        # Elimina cache existente
        try:
            await redis_client.delete(f'groups:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'Error al eliminar cache en Redis: {e}')


        return {'detail': 'Se ha creado un nuevo grupo de forma exitosa'}

    except SQLAlchemyError as e:
        logger.error(f'Error al crear un grupo {e}')
        await session.rollback()
        raise exceptions.DatabaseError(error=e, func='create_group')

@router.patch(
        '/{group_id}',
        description=""" Permite al usuario autenticado con rol Administrador el cambiar informacion del grupo,
                        puede ser el 'name' o 'description'.""",
        responses={
            200:{'description':'Grupo actualizado', 'model':responses.GroupUpdateSucces},
            401:{'description':'Usuario no autorizado', 'model':responses.NotAuthorized},
            404:{'description':'Grupo no encontrado', 'model':responses.NotFound},
            500:{'description':'error interno', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("15/minute")
async def update_group(
        request: Request,
        group_id: int,
        updated_group: schemas.UpdateGroup,
        auth_data: dict = Depends(require_role(roles=['admin', 'editor'])),
        session: AsyncSession = Depends(get_async_session)):

    try:
        found_group = get_group_or_404(group_id, session)
        
        if updated_group.name and found_group.name != updated_group.name:
            found_group.name = updated_group.name
            
        if updated_group.description and found_group.description != updated_group.description:
            found_group.description = updated_group.description
        
        await session.commit()

        # Elimina cache existente
        try:
            await redis_client.delete(f'groups:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'Error al eliminar cache en Redis: {e}')

        return {'detail':'Se ha actualizado la informacion del grupo'}
    
    except SQLAlchemyError as e:
        logger.error(f'Error al actualizar el grupo {e}')
        await session.rollback()
        raise exceptions.DatabaseError(error=e, func='update_group')

@router.delete(
        '/{group_id}',
        description='Permite al usuario autenticado con rol Administrador el eliminar al grupo.',
        responses={
            200:{'description':'Grupo actualizado', 'model':responses.GroupDeleteSucces},
            401:{'description':'Usuario no autorizado', 'model':responses.NotAuthorized},
            404:{'description':'Grupo no encontrado', 'model':responses.NotFound},
            500:{'description':'error interno', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("5/minute")
async def delete_group(
        request: Request,
        group_id: int,
        auth_data: dict = Depends(require_role(roles=['admin'])),
        session: AsyncSession = Depends(get_async_session)):

    try:
        # found_group = get_group_or_404(group_id, session)

        found_group = await session.get(db_models.Group, group_id)

        session.delete(found_group)
        await session.commit()

        # Elimina cache existente
        try:
            await redis_client.delete(f'groups:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'Error al eliminar cache en Redis: {e}')

        return {'detail':'Se ha eliminado el grupo'}

    except SQLAlchemyError as e:
        logger.error(f'Error al eliminar el grupo {e}')
        await session.rollback()
        raise exceptions.DatabaseError(error=e, func='delete_group')

@router.get(
        '/me',
        description=""" Obtiene todos los grupos a los que pertenece el usuario con informacion limitada.
                        'skip' recibe un int que saltea el resultado obtenido.
                        'limit' recibe un int para limitar los resultados obtenidos.""",
        responses={
            200:{'description':'Grupo donde esta el usuario obtenidos', 'model':schemas.ReadGroup},
            500:{'description':'error interno', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("60/minute")
async def get_groups_in_user(
        request: Request,
        limit:int = 10,
        skip: int = 0,
        user:db_models.User = Depends(auth_user),
        session:Session = Depends(get_session)) -> List[schemas.ReadGroup]:

    try:
        key = f'groups:user_id:{user.user_id}:limit:{limit}:offset:{skip}'
        # Busca si existe una respuesta guardada y la busca
        cached = await redis_client.get(key)

        if cached:
            logger.info(f'Redis Cache {key}')
            decoded = json.loads(cached)
            return decoded

        statement = (select(db_models.Group)
                    .join(db_models.group_user, db_models.group_user.group_id == db_models.Group.group_id)
                    .where(db_models.group_user.user_id == user.user_id)
                    .order_by(db_models.Group.group_id)
                    .limit(limit).offset(skip))

        found_group = session.exec(statement).all()

        # Cachea la respuesta
        to_cache = [
            {
                **group.model_dump(),
                'users': [user.model_dump() for user in group.users]
            }
            for group in found_group]

        # Guarda la respuesta
        await redis_client.setex(key, 600, json.dumps(to_cache, default=str))

        return to_cache

    except SQLAlchemyError as e:
        logger.error(f'Error al obtener los grupos donde pertenece el usuario {e}')
        raise exceptions.DatabaseError(error=e, func='get_groups_in_user')

@router.post(
        '/{group_id}/{user_id}',
        description='Permite al usuario autenticado con rol Administrador el agregar un nuevo usuario al grupo',
        responses={
                200:{'description':'Usuario agregado al grupo', 'model':responses.GroupAppendUserSucces},
                400:{'description':'request error', 'model':responses.ErrorInRequest},
                401:{'description':'Usuario no autorizado', 'model':responses.NotAuthorized},
                404:{'description':'Grupo no encontrado', 'model':responses.NotFound},
                500:{'description':'error interno', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("20/minute")
async def append_user_group(
        request: Request,
        group_id: int,
        user_id: int,
        auth_data: dict = Depends(require_role(roles=['admin', 'editor'])),
        session: AsyncSession = Depends(get_async_session)):

    try:
        actual_role = auth_data['role']
        actual_user = auth_data['user']

        found_group = get_group_or_404(group_id, session)

        # Busca el usuario
        new_user = get_user_or_404(user_id, session)

        if new_user in found_group.users:
            logger.error(f'El user {user_id} ya existe en el grupo {group_id}')
            raise exceptions.UserInGroupError(user_id=new_user.user_id, group_id=found_group.group_id)

        # Lo agrega al grupo
        await found_group.users.append(new_user)
        await session.commit()

        # Se crea la notificacion
        outgoing_payload = schemas.OutgoingNotificationPayload(
            notification_type='append_to_group',
            message=f'Has sido agregado a group {group_id}',
            timestamp=datetime.now())

        # Crea el evento
        outgoing_event = schemas.WebSocketEvent(
            type='notification',
            payload=outgoing_payload.model_dump()
        )

        # Parsea el evento
        outgoing_event_json = outgoing_event.model_dump_json()

        # Envia el evento
        await manager.send_to_user(message_json_string=outgoing_event_json, user_id=user_id)

        # Elimina cache existente
        try:
            await redis_client.delete(f'groups:user_id:{actual_user.user_id}:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'Error al eliminar cache en Redis: {e}')

        return {'detail':'El usuario ha sido agregado al grupo'}

    except SQLAlchemyError as e:
        logger.error(f'Error al agregar un usuario al grupo {e}')
        await session.rollback()
        raise exceptions.DatabaseError(error=e, func='append_user_group')

@router.delete(
        '/{group_id}/{user_id}',
        description='Permite al usuario autenticado con rol Administrador el eliminar un usuario del grupo',
        responses={
                200:{'description':'Usuario eliminado del Grupo', 'model':responses.GroupDeleteUserSucces},
                400:{'description':'request error', 'model':responses.ErrorInRequest},
                401:{'description':'Usuario no autorizado', 'model':responses.NotAuthorized},
                404:{'description':'Grupo no encontrado', 'model':responses.NotFound},
                500:{'description':'error interno', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("5/minute")
async def delete_user_group(  
        request: Request,
        group_id: int,
        user_id: int,
        auth_data: dict = Depends(require_role(roles=['admin', 'editor'])),
        session: AsyncSession = Depends(get_async_session)):

    try:
        actual_role = auth_data['role']
        actual_user = auth_data['user']

        found_group = get_group_or_404(group_id, session)

        # Busca el usuario
        found_user = get_user_or_404(user_id, session)

        if found_user in found_group.users:
            # Lo elimina del grupo

            role_user = role_of_user_in_group(user_id=found_user.user_id, group_id=group_id, session=session)

            if role_user in ['editor', 'member'] and actual_role == 'admin' or role_user == 'member' and actual_role == 'editor':            
                found_group.users.remove(found_user)
                await session.commit()

                # Se crea la notificacion
                outgoing_payload = schemas.OutgoingNotificationPayload(
                    notification_type='remove_user_to_group',
                    message=f'Fuiste removido del group {group_id}',
                    timestamp=datetime.now())

                # Crea el evento
                outgoing_event = schemas.WebSocketEvent(
                    type='notification',
                    payload=outgoing_payload.model_dump()
                )

                # Parsea el evento
                outgoing_event_json = outgoing_event.model_dump_json()

                # Envia el evento
                await manager.send_to_user(message_json_string=outgoing_event_json, user_id=user_id)

                logger.info(f'User {user_id} eliminado del Group {group_id} por {actual_user.user_id}')

                # Elimina cache existente
                try:
                    await redis_client.delete(f'groups:user_id:{actual_user.user_id}:limit:*:offset:*')
                except redis.RedisError as e:
                    logger.warning(f'Error al eliminar cache en Redis: {e}')

                return {'detail':'El usuario ha sido eliminado al grupo'}

            raise exceptions.NotAuthorized(actual_user.user_id)

        else:
            logger.error(f'El user {user_id} no se encontro en el grupo {group_id}')
            raise exceptions.UserNotFoundError(user_id)

    except SQLAlchemyError as e:
        logger.error(f'Error al eliminar un usuario del grupo {e}')
        await session.rollback()
        raise exceptions.DatabaseError(error=e, func='delete_user_group')

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
        session: AsyncSession = Depends(get_async_session)):

    try:
        actual_user = auth_data['user']

        get_group_or_404(group_id, session)

        # Busca el usuario
        statement = (select(db_models.group_user)
                    .join(db_models.Group, db_models.group_user.group_id == db_models.Group.group_id)
                    .where(db_models.group_user.user_id == user_id))

        result = session.exec(statement)
        found_user = result.first()

        if not found_user:
            logger.error(f'No se encontro el user {user_id} en el grupo {group_id}')
            raise exceptions.UserNotInGroupError(user_id=user_id, group_id=group_id)
        
        found_user.role = update_role.role
        
        await session.commit()
        await session.refresh(found_user)

        # Se crea la notificacion
        outgoing_payload = schemas.OutgoingNotificationPayload(
            notification_type='update_role_to_group',
            message=f'Tu rol en group {group_id} fue actualizado a: {found_user.role.value}',
            timestamp=datetime.now())

        # Crea el evento
        outgoing_event = schemas.WebSocketEvent(
            type='notification',
            payload=outgoing_payload.model_dump()
        )

        # Parsea el evento
        outgoing_event_json = outgoing_event.model_dump_json()

        # Envia el evento
        await manager.send_to_user(message_json_string=outgoing_event_json, user_id=user_id)

        # Elimina cache existente
        try:
            await redis_client.delete(f'groups:user_id:{actual_user.user_id}:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'Error al eliminar cache en Redis: {e}')

        return {'detail':'Se ha cambiado los permisos del usuario en el grupo'}

    except SQLAlchemyError as e:
        logger.error(f'Error al actualizar el usuario en el grupo')
        await session.rollback()
        raise exceptions.DatabaseError(error=e, func='update_user_group')

@router.get(
        '/{group_id}/users',
        description=""" Obtiene todos los usuarios de un grupo.
                        'skip' recibe un int que saltea el resultado obtenido.
                        'limit' recibe un int para limitar los resultados obtenidos.""",
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
        user: db_models.User = Depends(auth_user),
        session:AsyncSession = Depends(get_async_session)) -> List[schemas.ReadGroupUser]:

    try:
        key = f'groups:users:group_id:{group_id}:limit:{limit}:offset:{skip}'
        # Busca si existe una respuesta guardada y la busca
        cached = await redis_client.get(key)

        if cached:
            logger.info(f'Redis Cache: {key}')
            decoded = json.loads(cached)
            return decoded

        get_group_or_404(group_id, session)

        statement = (select(db_models.User.username, db_models.User.user_id, db_models.group_user.role)
                    .join(db_models.group_user, db_models.group_user.user_id == db_models.User.user_id)
                    .where(db_models.group_user.group_id == group_id)
                    .limit(limit).offset(skip))

        search = await session.exec(statement)
        results = search.all()

        # Cachea la respuesta
        to_cache = [
            schemas.ReadGroupUser(user_id=user_id, username=username, role=role.value)
            for username, user_id, role in results
            ]

        # Guarda la respuesta
        try:
            await redis_client.setex(key, 600, json.dumps([user_.model_dump() for user_ in to_cache], default=str))
        except redis.RedisError as e:
            logger.warning(f'Error al cachear en Redis: {e}')

        return to_cache

    except SQLAlchemyError as e:
        logger.error(f'Error al obtener los usuarios del grupo {e}')
        await session.rollback()
        raise exceptions.DatabaseError(error=e, func='get_user_in_group')