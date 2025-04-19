from fastapi import APIRouter, status, HTTPException, Depends
from models import db_models, schemas
from db.database import get_session, Session, select, SQLAlchemyError, or_
from typing import List
from .auth import encrypt_password, auth_user

router = APIRouter(tags=['User'])

@router.get('/user', description='Obtiene los usuarios')
def get_users(session:Session = Depends(get_session)) -> List[schemas.ReadUser]:
    try:
        statement = select(db_models.User)
        found_users = session.exec(statement).all()
        return found_users
    except SQLAlchemyError as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'error en get_users: {str(e)}')

@router.post('/user', description='Crea un nuevo usuario') 
def create_user( new_user: schemas.CreateUser,
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
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'error en create_user: {str(e)}')

@router.get('/user/me', description='Obtiene el usuario actual')
def get_users(user: db_models.User = Depends(auth_user)) -> schemas.ReadUser:
    try:
        return user
    except SQLAlchemyError as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'error en get_users: {str(e)}')

@router.patch('/user/me', description='Actualiza un usuario')
def update_user(updated_user: schemas.UpdateUser,
                user: db_models.User = Depends(auth_user),
                session: Session = Depends(get_session)): 

    try:
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el usuario')
        
        if user.username != updated_user.username and updated_user.username:
            user.username = updated_user.username

        if user.email != updated_user.email and updated_user.email:
            user.email = updated_user.email
        
        session.commit()
        
        return {'detail':'Se ha actualizado el usuario'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'error en update_user: {str(e)}')

@router.delete('/user/me', description='Elimina un usuario especifico')
def delete_user(user: db_models.User = Depends(auth_user),
                session: Session = Depends(get_session)):

    try:
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el proyecto')
        
        session.delete(user)
        session.commit()
        
        return {'detail':'Se ha eliminado el usuario'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'error en delete_user: {str(e)}')