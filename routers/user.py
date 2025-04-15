from fastapi import APIRouter, status, HTTPException, Depends
from models import db_models, schemas
from db.database import get_session, Session, select, SQLAlchemyError, or_
from typing import List
from .auth import encrypt_password

router = APIRouter(tags=['User'])

@router.get('/user', description='Obtiene los usuarios')
def get_users(session:Session = Depends(get_session)) -> List[schemas.ReadUser]:
    try:
        statement = select(db_models.User)
        found_users = session.exec(statement).all()
        return found_users
    except SQLAlchemyError as e:
        raise {'error en get_users': f'error {e}'}

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
        raise {'error en create_user':f'error {e}'}

@router.patch('/user/{user_id}', description='Actualiza un usuario')
def update_user(user_id: int,
                updated_user: schemas.UpdateUser,
                session: Session = Depends(get_session)): 

    try:
        founded_user = session.get(db_models.User, user_id)
        
        if not founded_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el usuario')
        
        if founded_user.username != updated_user.username and updated_user.username:
            founded_user.username = updated_user.username

        if founded_user.email != updated_user.email and updated_user.email:
            founded_user.email = updated_user.email
        
        session.commit()
        
        return {'detail':'Se ha actualizado el usuario'}
    
    except SQLAlchemyError as e:
        raise {'error en update_user':f'error {e}'}

@router.delete('/user/{user_id}', description='Elimina un usuario especifico')
def delete_user(user_id: int,
                session: Session = Depends(get_session)):

    try:
        founded_user = session.get(db_models.User, user_id)
        
        if not founded_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el proyecto')
        
        session.delete(founded_user)
        session.commit()
        
        return {'detail':'Se ha eliminado el usuario'}
    
    except SQLAlchemyError as e:
        raise {'error en delete_user':f'error {e}'}