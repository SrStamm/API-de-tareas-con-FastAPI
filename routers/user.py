from fastapi import APIRouter, status, HTTPException, Depends
from models import db_models, schemas, exceptions
from db.database import get_session, Session, select, SQLAlchemyError, or_
from typing import List
from .auth import encrypt_password, auth_user

router = APIRouter(prefix='/user', tags=['User'])

@router.get('', description='Obtiene los usuarios')
def get_users(session:Session = Depends(get_session)) -> List[schemas.ReadUser]:
    try:
        statement = select(db_models.User)
        found_users = session.exec(statement).all()
        return found_users
    except SQLAlchemyError as e:
        raise exceptions.DatabaseError(error=e, func='get_users')

@router.post('', description='Crea un nuevo usuario') 
def create_user(new_user: schemas.CreateUser,
                session:Session = Depends(get_session)):
    try:
        statement = select(db_models.User).where(or_(db_models.User.email == new_user.email, db_models.User.username == new_user.username))
        founded_user = session.exec(statement).first()

        if founded_user:
            if founded_user.username == new_user.username:
                raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, detail='Ya existe un usuario con este Username')
            else:
                raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, detail='Ya existe un usuario con este Email')

        new_user = db_models.User(**new_user.model_dump())

        new_user.password = encrypt_password(new_user.password)
        
        session.add(new_user)
        session.commit()

        return {'detail':'Se ha creado un nuevo usuario con exito'}

    except SQLAlchemyError as e:
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='create_user')

@router.get('/me', description='Obtiene informacion del usuario actual')
def get_users(user: db_models.User = Depends(auth_user)) -> schemas.ReadUser:
    try:
        return user
    except SQLAlchemyError as e:
        raise exceptions.DatabaseError(error=e, func='get_users')

@router.patch('/me', description='Actualiza el usuario actual')
def update_user(updated_user: schemas.UpdateUser,
                user: db_models.User = Depends(auth_user),
                session: Session = Depends(get_session)): 

    try:        
        if user.username != updated_user.username and updated_user.username:
            user.username = updated_user.username

        if user.email != updated_user.email and updated_user.email:
            user.email = updated_user.email
        
        session.commit()
        
        return {'detail':'Se ha actualizado el usuario'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='update_user')

@router.delete('/me', description='Elimina el usuario actual')
def delete_user(user: db_models.User = Depends(auth_user),
                session: Session = Depends(get_session)):

    try:
        session.delete(user)
        session.commit()
        
        return {'detail':'Se ha eliminado el usuario'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='delete_user')