from fastapi import APIRouter, status, HTTPException, Depends
from models import db_models, schemas
from db.database import get_session, Session, select, SQLAlchemyError
from typing import List
from .auth import auth_user

router = APIRouter(prefix='/group', tags=['Group'])

def is_admin_in_group(user, group_id, session: Session):
    stmt = (select(db_models.group_user)
                     .where(db_models.group_user.user_id == user.user_id, db_models.group_user.group_id == group_id))
    
    found_user = session.exec(stmt).first()

    if not found_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el usuario')
    
    if found_user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='No estas autorizado')

def get_group_or_404(group_id: int, session: Session):
    statement = select(db_models.Group).where(db_models.Group.group_id == group_id)
    group = session.exec(statement).first()
        
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el grupo')
    
    return group

def get_user_or_404(user_id: int, session: Session):
    statement = (select(db_models.User).where(db_models.User.user_id == user_id))
        
    user = session.exec(statement).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el usuario')

    return user

@router.get('', description='Obtiene todos los grupos')
def get_groups(session:Session = Depends(get_session)) -> List[schemas.ReadGroup]:
    try:
        statement = (select(db_models.Group).order_by(db_models.Group.group_id))
        found_group = session.exec(statement).all()
        return found_group

    except SQLAlchemyError as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'error {str(e)}')

@router.post('', description='Crea un nuevo grupo')
def create_group(new_group: schemas.CreateGroup,
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

        return {'detail': 'Se ha creado un nuevo grupo de forma exitosa'}

    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f'Error al crear el grupo: {str(e)}')

@router.patch('/{group_id}', description='Actualiza a un grupo')
def update_group(group_id: int,
                 updated_group: schemas.UpdateGroup,
                 user: db_models.User = Depends(auth_user),
                 session: Session = Depends(get_session)):

    try:
        is_admin_in_group(user, group_id, session)

        founded_group = get_group_or_404(group_id, session)
        
        if updated_group.name is not None:
            founded_group.name = updated_group.name
            
        if updated_group.description is not None:
            founded_group.description = updated_group.description
        
        session.commit()
        
        return {'detail':'Se ha actualizado la informacion del grupo'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(500, detail=f'Error {str(e)}')

@router.delete('/{group_id}', description='Elimina un grupo especifico')
def delete_group(group_id: int,
                 user: db_models.User = Depends(auth_user),
                 session: Session = Depends(get_session)):

    try:
        is_admin_in_group(user, group_id, session)

        founded_group = get_group_or_404(group_id, session)
        
        session.delete(founded_group)
        session.commit()
        
        return {'detail':'Se ha eliminado el grupo'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'error en delete_group: {str(e)}')

@router.get('/me', description='Obtiene todos los grupos')
def get_groups_in_user(user:db_models.User = Depends(auth_user),
                       session:Session = Depends(get_session)) -> List[schemas.ReadBasicDataGroup]:
    try:
        statement = (select(db_models.Group)
                     .join(db_models.group_user, db_models.group_user.group_id == db_models.Group.group_id)
                     .where(db_models.group_user.user_id == user.user_id)
                     .order_by(db_models.Group.group_id))
        found_group = session.exec(statement).all()
        return found_group
    
    except SQLAlchemyError as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'error {str(e)}')

@router.post('/{group_id}/{user_id}', description='Agrega un usuario al grupo')
def append_user_group(group_id: int,
                      user_id: int,
                      user: db_models.User = Depends(auth_user),
                      session: Session = Depends(get_session)):

    try:
        is_admin_in_group(user, group_id, session)

        founded_group = get_group_or_404(group_id, session)
        
        # Busca el usuario
        new_user = get_user_or_404(user_id, session)

        if new_user in founded_group.users:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='El usuario ya existe en el grupo')
        
        # Lo agrega al grupo
        founded_group.users.append(new_user)
        
        session.commit()
        
        return {'detail':'El usuario ha sido agregado al grupo'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'error en append_user_group: {str(e)}')

@router.delete('/{group_id}/{user_id}', description='Elimina un usuario del grupo')
def delete_user_group(group_id: int,
                      user_id: int,
                      user: db_models.User = Depends(auth_user),
                      session: Session = Depends(get_session)):

    try:
        is_admin_in_group(user, group_id, session)

        founded_group = get_group_or_404(group_id, session)
        
        # Busca el usuario
        found_user = get_user_or_404(user_id, session)

        if not founded_group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el usuario')

        if found_user in founded_group.users:
            # Lo elimina del grupo
            founded_group.users.remove(found_user)
            session.commit()
            
            return {'detail':'El usuario ha sido eliminado al grupo'}
        
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='El usuario no esta en el grupo')
    
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'error en delete_user_group: {str(e)}')

@router.patch('/{group_id}/{user_id}', description='Modifica el rol de un usuario en un grupo')
def update_user_group(group_id: int,
                        user_id: int,
                        update_role: schemas.UpdateRoleUser,
                        user: db_models.User = Depends(auth_user),
                        session: Session = Depends(get_session)):

    try:
        is_admin_in_group(user, group_id, session)

        founded_group = get_group_or_404(group_id, session)

        # Busca el usuario
        statement = (select(db_models.group_user)
                     .join(db_models.Group, db_models.group_user.group_id == db_models.Group.group_id)
                     .where(db_models.group_user.user_id == user_id))

        found_user = session.exec(statement).first()

        if not found_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el usuario')

        found_user.role = update_role.role
        
        session.commit()

        return {'detail':'Se ha cambiado los permisos del usuario en el grupo'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'error en append_user_group: {str(e)}')

@router.get('/{group_id}/users', description='Obtiene todos los grupos')
def get_user_in_group(group_id: int,
                      session:Session = Depends(get_session)
                    ) -> List[schemas.ReadGroupUser]:

    try:
        statement = (select(db_models.User, db_models.group_user.role)
                    .join(db_models.group_user, db_models.group_user.user_id == db_models.User.user_id)
                    .where(db_models.group_user.group_id == group_id))
        
        results = session.exec(statement).all()
        
        # El resultado son tuplas, entonces se debe hacer lo siguiente para que devuelva la informacion solicitada
        return [
            schemas.ReadGroupUser(user_id=user.user_id, username=user.username, role=role)
            for user, role in results
        ]
    
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'error en append_user_group: {str(e)}')