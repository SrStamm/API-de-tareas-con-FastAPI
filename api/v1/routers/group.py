from fastapi import APIRouter, Depends, Request
from models import db_models, schemas, exceptions, responses
from db.database import get_session, Session, select, selectinload, SQLAlchemyError, redis_client, redis
from typing import List
from .auth import auth_user
from core.utils import get_group_or_404, get_user_or_404
from core.permission import require_role, role_of_user_in_group
from core.logger import logger
from core.limiter import limiter
from .ws import manager
from datetime import datetime
import json

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
        session: Session = Depends(get_session)) -> List[schemas.ReadBasicDataGroup]: 

    try:
        key = f'groups:limit:{limit}:offset:{skip}'
        # Busca si existe una respuesta guardada y la busca
        cached = await redis_client.get(key)

        if cached:
            logger.info(f'[get_groups] Cache HIT - Key: {key}')
            decoded = json.loads(cached)
            return decoded

        stmt = (select(db_models.Group)
                    .options(selectinload(db_models.Group.users))
                    .order_by(db_models.Group.group_id).limit(limit).offset(skip))

        found_group = session.exec(stmt).all()

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
            logger.info(f'[get_groups] Cache SET - Key: {key}')
        except redis.RedisError as e:
            logger.warning(f'[get_groups] Redis Cache FAIL - Key: {key} | Error: {e}') 

        return to_cache

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
        user: db_models.User = Depends(auth_user),
        session: Session = Depends(get_session)):
    try:
        # Crear el grupo con el usuario creador
        group = db_models.Group(**new_group.model_dump())
        session.add(group)
        session.commit()
        session.refresh(group)

        # Agregar al usuario creador al grupo con el rol de administrador
        group_user = db_models.group_user(
            group_id=group.group_id,
            user_id=user.user_id,
            role=db_models.Group_Role.ADMIN
        )
        session.add(group_user)
        session.commit()


        # Elimina cache existente
        try:
            await redis_client.delete(f'groups:limit:*:offset:*')
            logger.info(f'[create_group] Redis Cache Delete - Key: groups:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'[create_group] Redis Cache Delete Error | Error: {str(e)}')

        logger.info(f'[create_group] Group Create Success')
        return {'detail': 'Se ha creado un nuevo grupo de forma exitosa'}

    except SQLAlchemyError as e:
        logger.error(f'[create_group] Database Error:  {str(e)}')
        session.rollback()
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
        session: Session = Depends(get_session)):

    try:
        found_group = get_group_or_404(group_id, session)

        if updated_group.name and found_group.name != updated_group.name:
            found_group.name = updated_group.name

        if updated_group.description and found_group.description != updated_group.description:
            found_group.description = updated_group.description

        session.commit()

        # Elimina cache existente
        try:
            await redis_client.delete(f'groups:limit:*:offset:*')
            logger.info(f'[update_group] Redis Cache Delete - Key: groups:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'[update_group] Redis Cache Delete Error | Error: {str(e)}')

        logger.info(f'[update_group] Group Create Success')
        return {'detail':'Se ha actualizado la informacion del grupo'}

    except SQLAlchemyError as e:
        logger.error(f'[update_group] Database Error:  {str(e)}')
        session.rollback()
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
        session: Session = Depends(get_session)):

    try:
        # found_group = get_group_or_404(group_id, session)

        found_group = session.get(db_models.Group, group_id)

        session.delete(found_group)
        session.commit()

        # Elimina cache existente
        try:
            await redis_client.delete(f'groups:limit:*:offset:*')
            logger.info(f'[delete_group] Redis Cache Delete - Key: groups:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'[delete_group] Redis Cache Delete Error | Error: {str(e)}')

        return {'detail':'Se ha eliminado el grupo'}

    except SQLAlchemyError as e:
        logger.error(f'[delete_group] Database Error:  {str(e)}')
        session.rollback()
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
        user:db_models.User = Depends(auth_user),
        session:Session = Depends(get_session)) -> List[schemas.ReadGroup]:

    try:
        key = f'groups:user_id:{user.user_id}:limit:{limit}:offset:{skip}'
        # Busca si existe una respuesta guardada y la busca
        cached = await redis_client.get(key)

        if cached:
            logger.info(f'[get_groups_in_user] Cache Hit - Key: {str(key)}')
            decoded = json.loads(cached)
            return decoded

        stmt = (select(db_models.Group)
                    .join(db_models.group_user, db_models.group_user.group_id == db_models.Group.group_id)
                    .where(db_models.group_user.user_id == user.user_id)
                    .order_by(db_models.Group.group_id)
                    .limit(limit).offset(skip))

        found_group = session.exec(stmt).all()

        # Cachea la respuesta
        to_cache = [
            {
                **group.model_dump(),
                'users': [user.model_dump() for user in group.users]
            }
            for group in found_group]

        # Guarda la respuesta
        try:
            await redis_client.setex(key, 600, json.dumps(to_cache, default=str))
            logger.info(f'[get_groups_in_user] Redis Cache Set - Key: {str(key)}')
        except redis.RedisError as e:
            logger.warning(f'[get_groups_in_user] Redis Cache Set Error | Error: {str(e)}')

        return to_cache

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
        session: Session = Depends(get_session)):

    try:
        actual_role = auth_data['role']
        actual_user = auth_data['user']

        found_group = get_group_or_404(group_id, session)

        # Busca el usuario
        new_user = get_user_or_404(user_id, session)

        if new_user in found_group.users:
            logger.error(f'[append_user_group] User {user_id} Append to Group {group_id} Error')
            raise exceptions.UserInGroupError(user_id=new_user.user_id, group_id=found_group.group_id)

        # Lo agrega al grupo
        found_group.users.append(new_user)
        session.commit()

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
        await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

        # Elimina cache existente
        try:
            await redis_client.delete(f'groups:user_id:{actual_user.user_id}:limit:*:offset:*')
            logger.info(f'[append_user_group] Redis Cache Delete - Key: groups:user_id:{actual_user.user_id}:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'[append_user_group] Redis Cache Delete Error | Error: {str(e)}')

        logger.info(f'[append_user_group] User {user_id} Append to Group {group_id} Success')
        return {'detail':'El usuario ha sido agregado al grupo'}

    except SQLAlchemyError as e:
        logger.error(f'[append_user_group] Database Error:  {str(e)}')
        session.rollback()
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
        session: Session = Depends(get_session)):

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
                session.commit()

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
                await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

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
        logger.error(f'[delete_user_group] Database Error:  {str(e)}')
        session.rollback()
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
        session: Session = Depends(get_session)):

    try:
        actual_user = auth_data['user']

        get_group_or_404(group_id, session)

        # Busca el usuario
        stmt = (select(db_models.group_user)
                    .join(db_models.Group, db_models.group_user.group_id == db_models.Group.group_id)
                    .where(db_models.group_user.user_id == user_id))

        result = session.exec(stmt)
        found_user = result.first()

        if not found_user:
            logger.error(f'No se encontro el user {user_id} en el grupo {group_id}')
            raise exceptions.UserNotInGroupError(user_id=user_id, group_id=group_id)
        
        found_user.role = update_role.role
        
        session.commit()
        session.refresh(found_user)

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
        await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

        # Elimina cache existente
        try:
            await redis_client.delete(f'groups:user_id:{actual_user.user_id}:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'Error al eliminar cache en Redis: {e}')

        return {'detail':'Se ha cambiado los permisos del usuario en el grupo'}

    except SQLAlchemyError as e:
        logger.error(f'[update_user_group] Database Error:  {str(e)}')
        session.rollback()
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
        user: db_models.User = Depends(auth_user),
        session: Session = Depends(get_session)) -> List[schemas.ReadGroupUser]:

    try:
        key = f'groups:users:group_id:{group_id}:limit:{limit}:offset:{skip}'
        cached = await redis_client.get(key)

        if cached:
            logger.info(f'Redis Cache: {key}')
            decoded = json.loads(cached)
            return decoded

        get_group_or_404(group_id, session)

        stmt = (select(db_models.User.username, db_models.User.user_id, db_models.group_user.role)
                    .join(db_models.group_user, db_models.group_user.user_id == db_models.User.user_id)
                    .where(db_models.group_user.group_id == group_id)
                    .limit(limit).offset(skip))

        results = session.exec(stmt).all()

        to_cache = [
            schemas.ReadGroupUser(user_id=user_id, username=username, role=role.value)
            for username, user_id, role in results
            ]

        try:
            await redis_client.setex(key, 600, json.dumps([user_.model_dump() for user_ in to_cache], default=str))
        except redis.RedisError as e:
            logger.warning(f'Error al cachear en Redis: {e}')

        return to_cache

    except SQLAlchemyError as e:
        logger.error(f'[get_user_in_group] Database Error:  {str(e)}')
        raise exceptions.DatabaseError(error=e, func='get_groups')
    except Exception as e:
        logger.error(f'[get_user_in_group] Unexpected Error:  {str(e)}')
        raise