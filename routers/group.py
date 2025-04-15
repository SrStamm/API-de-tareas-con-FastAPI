from fastapi import APIRouter, status, HTTPException, Depends
from models import db_models, schemas
from db.database import get_session, Session, select, SQLAlchemyError
from typing import List

router = APIRouter(prefix='/group', tags=['Group'])

@router.get('', description='Obtiene todos los grupos')
def get_groups(session:Session = Depends(get_session)) -> List[schemas.ReadGroup]:
    statement = select(db_models.Group)
    found_group = session.exec(statement).all()
    return found_group

@router.post('', description='Crea un nuevo grupo')
def create_group( new_group: schemas.CreateGroup,
                  session:Session = Depends(get_session)):
    try:
        new_group = db_models.Group(**new_group.model_dump())
        session.add(new_group)
        session.commit()
        return {'detail':'Se ha creado un nuevo grupo de forma exitosa'}
    except SQLAlchemyError as e:
        raise {'error en create_group':f'error {e}'}

@router.patch('/{group_id}', description='Actualiza a un grupo')
def update_group(group_id: int,
                 updated_group: schemas.UpdateGroup,
                 session: Session = Depends(get_session)):

    try:
        statement = select(db_models.Group).where(db_models.Group.group_id == group_id)
        founded_group = session.exec(statement).first()
        
        if not founded_group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el grupo')
        
        if founded_group.name != updated_group.name:
            founded_group.name = updated_group.name
            
        if founded_group.description != updated_group.description:
            founded_group.description = updated_group.description
        
        session.commit()
        
        return {'detail':'Se ha actualizado la informacion del grupo'}
    
    except SQLAlchemyError as e:
        raise {'error en update_group':f'error {e}'}

@router.delete('/{group_id}', description='Elimina un grupo especifico')
def delete_group(group_id: int,
                 session: Session = Depends(get_session)):

    try:
        statement = select(db_models.Group).where(db_models.Group.group_id == group_id)
        founded_group = session.exec(statement).first()
        
        if not founded_group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el grupo')
        
        session.delete(founded_group)
        session.commit()
        
        return {'detail':'Se ha eliminado el grupo'}
    
    except SQLAlchemyError as e:
        raise {'error en delete_group':f'error {e}'}


@router.post('/{group_id}/{user_id}', description='Agrega un usuario al grupo')
def append_user_group(group_id: int,
                      user_id: int,
                      session: Session = Depends(get_session)):

    try:
        statement = (select(db_models.Group)
                     .where(db_models.Group.group_id == group_id))
        
        founded_group = session.exec(statement).first()

        if not founded_group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No existe o no se encontro el grupo')
        
        # Busca el usuario
        statement = (select(db_models.User)
                            .where(db_models.User.user_id == user_id))
        
        user = session.exec(statement).first()

        if not founded_group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el usuario')

        if user in founded_group.users:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='El usuario ya existe en el grupo')
        
        # Lo agrega al grupo
        founded_group.users.append(user)
        
        session.commit()
        
        return {'detail':'El usuario ha sido agregado al grupo'}
    
    except SQLAlchemyError as e:
        raise {'error en append_user_group':f'error {e}'}

@router.delete('/{group_id}/{user_id}', description='Elimina un usuario del grupo')
def delete_user_group(group_id: int,
                      user_id: int,
                      session: Session = Depends(get_session)):

    try:
        statement = (select(db_models.Group)
                    .where(db_models.Group.group_id == group_id))
        
        founded_group = session.exec(statement).first()

        if not founded_group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No existe o no se encontro el grupo')
        
        # Busca el usuario
        statement = (select(db_models.User)
                            .where(db_models.User.user_id == user_id))
        
        user = session.exec(statement).first()

        if not founded_group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el usuario')

        if user in founded_group.users:
            # Lo elimina del grupo
            founded_group.users.remove(user)
            session.commit()
            
            return {'detail':'El usuario ha sido eliminado al grupo'}
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='El usuario no esta en el grupo')
    
    except SQLAlchemyError as e:
        raise {'error en delete_user_group':f'error {e}'}