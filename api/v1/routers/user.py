from fastapi import APIRouter, Depends, Request
from models import db_models, schemas, exceptions, responses
from db.database import get_session, Session, select, SQLAlchemyError, or_, redis_client
from typing import List
from .auth import encrypt_password, auth_user
from core.logger import logger
from core.limiter import limiter
import json

router = APIRouter(prefix='/user', tags=['User'])

@router.get(
        '',
        description=""" Obtain all of users.
                    'skip' receives an "int" that skips the result obtained.
                    'limit' receives an "int" that limits the result obtained.""",
        responses={ 200: {'description':'Users obtained','model':schemas.ReadUser},
                    500: {'description':'Internal error', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("20/minute")
async def get_users(
        request:Request,
        limit:int = 10,
        skip: int = 0,
        session:Session = Depends(get_session)) -> List[schemas.ReadUser]:
    try:
        key = f'users:limit:{limit}:offset:{skip}'
        cached = await redis_client.get(key)

        if cached:
            decoded = json.loads(cached)
            logger.info(f'Redis Cached {key}')
            return decoded

        stmt = select(db_models.User.user_id, db_models.User.username).limit(limit).offset(skip)
        found_users = session.exec(stmt).all()

        to_cache = [
            schemas.ReadUser(user_id=user_id, username=username)
            for user_id, username in found_users
            ]

        # Guarda la respuesta
        await redis_client.setex(key, 600, json.dumps([user_.model_dump() for user_ in to_cache], default=str))

        return to_cache

    except SQLAlchemyError as e:
        logger.error(f'Error al obtener los usuarios {e}')
        raise exceptions.DatabaseError(error=e, func='get_users')

@router.post(
        '',
        description="""Create a new user. Nedd a username, an email and a password""",
        responses={
            201: {'description':'User created', 'model':responses.UserCreateSucces},
            406: {'description':'Data conflict', 'model':responses.UserConflictError},
            500: {'description':'Internal error', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("5/minute")
async def create_user(
        request:Request,
        new_user: schemas.CreateUser,
        session:Session = Depends(get_session)):
    try:
        stmt = select(db_models.User).where(or_(db_models.User.email == new_user.email, db_models.User.username == new_user.username))
        found_user = session.exec(stmt).first()

        if found_user:
            if found_user.username == new_user.username:
                logger.error('Ya existe un user con el mismo username')
                raise exceptions.UserWithUsernameExist()
            elif found_user.email == new_user.email:
                logger.error('Ya existe un user con el mismo email')
                raise exceptions.UserWithEmailExist()

        new_user = db_models.User(**new_user.model_dump())

        new_user.password = encrypt_password(new_user.password)

        session.add(new_user)
        session.commit()

        await redis_client.delete(f'users:limit:*:offset:*')

        return {'detail':'Se ha creado un nuevo usuario con exito'}

    except SQLAlchemyError as e:
        logger.error(f'Error al crear el usuario {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='create_user')

@router.get(
        '/me',
        description='Obtain current user information',
        responses={ 200: {'description':'Obtained current user','model':schemas.ReadUser},
                    500: {'description':'Internal errro', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("20/minute")
def get_user_me(request:Request, user: db_models.User = Depends(auth_user)) -> schemas.ReadUser:
    try:
        return user
    except SQLAlchemyError as e:
        logger.error(f'Error al obtener el user {user.user_id} actual {e}')
        raise exceptions.DatabaseError(error=e, func='get_users')

@router.patch(
        '/me',
        description='Update current user',
        responses={ 200: {'description':'Current user updated', 'model': responses.UserUpdateSucces},
                    500: {'description':'Internal error', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("5/minute")
async def update_user_me(
        request:Request,
        updated_user: schemas.UpdateUser,
        user: db_models.User = Depends(auth_user),
        session: Session = Depends(get_session)): 

    try:        
        if user.username != updated_user.username and updated_user.username:
            user.username = updated_user.username

            await redis_client.delete(f'users:limit:*:offset:*')

        if user.email != updated_user.email and updated_user.email:
            user.email = updated_user.email
        
        session.commit()
        
        return {'detail':'Se ha actualizado el usuario con exito'}
    
    except SQLAlchemyError as e:
        logger.error(f'Error al actualizar el user {user.user_id} actual {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='update_user')

@router.delete(
        '/me',
        description='Delete current user',
        responses= {200: {'description':'Current user deleted', 'model':responses.UserDeleteSucces},
                    500: {'description':'Internal error', 'model':responses.DatabaseErrorResponse}})
@limiter.limit("5/minute")
async def delete_user_me(
        request:Request,
        user: db_models.User = Depends(auth_user),
        session: Session = Depends(get_session)):

    try:
        session.delete(user)
        session.commit()
        
        await redis_client.delete(f'users:limit:*:offset:*')

        return {'detail':'Se ha eliminado el usuario'}
    
    except SQLAlchemyError as e:
        logger.error(f'Error al eliminar el user {user.user_id} actual {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='delete_user')