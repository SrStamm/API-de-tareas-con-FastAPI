from fastapi import APIRouter, Depends
from models import db_models, schemas, exceptions, responses
from db.database import get_session, Session, select, SQLAlchemyError, or_
from typing import List
from .auth import encrypt_password, auth_user
from core.logger import logger

router = APIRouter(prefix='/user', tags=['User'])

@router.get('', description=
            """ Obtiene los usuarios.
                'skip' recibe un int que saltea el resultado obtenido.
                'limit' recibe un int para limitar los resultados obtenidos.""",
            responses={ 200: {'description':'Usuarios encontrados','model':schemas.ReadUser},
                        500: {'description':'error interno', 'model':responses.DatabaseErrorResponse}})
def get_users(
            limit:int = 10,
            skip: int = 0,
            session:Session = Depends(get_session)) -> List[schemas.ReadUser]:
    try:
        statement = select(db_models.User.user_id, db_models.User.username).limit(limit).offset(skip)
        found_users = session.exec(statement).all()
        return found_users
    
    except SQLAlchemyError as e:
        logger.error(f'Error al obtener los usuarios {e}')
        raise exceptions.DatabaseError(error=e, func='get_users')

@router.post('', description='Crea un nuevo usuario',
                responses={ 200: {'description':'Usuario creado', 'model':responses.UserCreateSucces},
                            406: {'description':'Conflicto de datos', 'model':responses.UserConflictError},
                            500: {'description':'error interno', 'model':responses.DatabaseErrorResponse}}) 
def create_user(new_user: schemas.CreateUser,
                session:Session = Depends(get_session)):
    try:
        statement = select(db_models.User).where(or_(db_models.User.email == new_user.email, db_models.User.username == new_user.username))
        found_user = session.exec(statement).first()

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

        return {'detail':'Se ha creado un nuevo usuario con exito'}

    except SQLAlchemyError as e:
        logger.error(f'Error al crear el usuario {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='create_user')

@router.get('/me', description='Obtiene informacion del usuario actual',
            responses={ 200: {'description':'Obtenido usuario actual','model':schemas.ReadUser},
                        500: {'description':'error interno', 'model':responses.DatabaseErrorResponse}})
def get_user_me(user: db_models.User = Depends(auth_user)) -> schemas.ReadUser:
    try:
        return user 
    
    except SQLAlchemyError as e:
        logger.error(f'Error al obtener el user {user.user_id} actual {e}')
        raise exceptions.DatabaseError(error=e, func='get_users')

@router.patch('/me', description='Actualiza el usuario actual',
                response_model= responses.UserUpdateSucces,
                responses={ 200: {'description':'Usuario actualizado', 'model': responses.UserUpdateSucces},
                            500: {'description':'error interno', 'model':responses.DatabaseErrorResponse}})
def update_user_me(updated_user: schemas.UpdateUser,
                user: db_models.User = Depends(auth_user),
                session: Session = Depends(get_session)): 

    try:        
        if user.username != updated_user.username and updated_user.username:
            user.username = updated_user.username

        if user.email != updated_user.email and updated_user.email:
            user.email = updated_user.email
        
        session.commit()
        
        return {'detail':'Se ha actualizado el usuario con exito'}
    
    except SQLAlchemyError as e:
        logger.error(f'Error al actualizar el user {user.user_id} actual {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='update_user')

@router.delete('/me', description='Elimina el usuario actual',
                response_model=responses.UserDeleteSucces,
                responses= {200: {'description':'Usuario actual eliminado', 'model':responses.UserDeleteSucces},
                            500: {'description':'error interno', 'model':responses.DatabaseErrorResponse}})
def delete_user_me(user: db_models.User = Depends(auth_user),
                session: Session = Depends(get_session)):

    try:
        session.delete(user)
        session.commit()
        
        return {'detail':'Se ha eliminado el usuario'}
    
    except SQLAlchemyError as e:
        logger.error(f'Error al eliminar el user {user.user_id} actual {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='delete_user')