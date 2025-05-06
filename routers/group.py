from fastapi import APIRouter, Depends
from models import db_models, schemas, exceptions, responses
from db.database import get_session, Session, select, selectinload, SQLAlchemyError
from typing import List
from .auth import auth_user
from utils import get_group_or_404, get_user_or_404, is_admin_in_group
from core.logger import logger

router = APIRouter(prefix='/group', tags=['Group'])

@router.get('', description='Obtiene todos los grupos',
            responses={
                200:{'description':'Grupos obtenidos', 'model':schemas.ReadGroup},
                500:{'description':'error interno', 'model':responses.DatabaseErrorResponse}
            })
def get_groups(session:Session = Depends(get_session)) -> List[schemas.ReadGroup]:
    try:
        statement = (select(db_models.Group)
                    .options(selectinload(db_models.Group.users))
                    .order_by(db_models.Group.group_id))
        
        found_group = session.exec(statement).all()
        return found_group

    except SQLAlchemyError as e:
        logger.error(f'Error al obtener los grupos {e}')
        raise exceptions.DatabaseError(error=e, func='get_groups')

@router.post('',
            description="""El usuario autenticado crea un nuevo grupo, necesita un 'name', y opcional 'description'.
                El usuario se agrega de forma automatica como Administrador""",
            
            responses={
                200:{'description':'Grupo creado', 'model':responses.GroupCreateSucces},
                500:{'description':'error interno', 'model':responses.DatabaseErrorResponse}
            })
def create_group(   new_group: schemas.CreateGroup,
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
        logger.error(f'Error al crear un grupo {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='create_group')

@router.patch('/{group_id}',
            description="""Permite al usuario autenticado con rol Administrador el cambiar informacion del grupo,
                            puede ser el 'name' o 'description'.""",
            responses={
                200:{'description':'Grupo actualizado', 'model':responses.GroupUpdateSucces},
                401:{'description':'Usuario no autorizado', 'model':responses.NotAuthorized},
                404:{'description':'Grupo no encontrado', 'model':responses.NotFound},
                500:{'description':'error interno', 'model':responses.DatabaseErrorResponse}
            })
def update_group(group_id: int,
                updated_group: schemas.UpdateGroup,
                user: db_models.User = Depends(auth_user),
                session: Session = Depends(get_session)):

    try:
        is_admin_in_group(user=user, group_id=group_id, session=session)

        found_group = get_group_or_404(group_id, session)
        
        if updated_group.name is not None:
            found_group.name = updated_group.name
            
        if updated_group.description is not None:
            found_group.description = updated_group.description
        
        session.commit()
        
        return {'detail':'Se ha actualizado la informacion del grupo'}
    
    except SQLAlchemyError as e:
        logger.error(f'Error al actualizar el grupo {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='update_group')

@router.delete('/{group_id}', description='Permite al usuario autenticado con rol Administrador el eliminar al grupo.',
                responses={
                    200:{'description':'Grupo actualizado', 'model':responses.GroupDeleteSucces},
                    401:{'description':'Usuario no autorizado', 'model':responses.NotAuthorized},
                    404:{'description':'Grupo no encontrado', 'model':responses.NotFound},
                    500:{'description':'error interno', 'model':responses.DatabaseErrorResponse}
            })
def delete_group(group_id: int,
                user: db_models.User = Depends(auth_user),
                session: Session = Depends(get_session)):

    try:
        found_group = get_group_or_404(group_id, session)
        
        is_admin_in_group(user, group_id, session)
        
        session.delete(found_group)
        session.commit()
        
        return {'detail':'Se ha eliminado el grupo'}
    
    except SQLAlchemyError as e:
        logger.error(f'Error al eliminar el grupo {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='delete_group')
    
@router.get('/me',
            description='Obtiene todos los grupos a los que pertenece el usuario autenticado',
            responses={
                200:{'description':'Grupo donde esta el usuario obtenidos', 'model':schemas.ReadBasicDataGroup},
                500:{'description':'error interno', 'model':responses.DatabaseErrorResponse}
            })
def get_groups_in_user( user:db_models.User = Depends(auth_user),
                        session:Session = Depends(get_session)) -> List[schemas.ReadBasicDataGroup]:
    try:
        statement = (select(db_models.Group)
                    .join(db_models.group_user, db_models.group_user.group_id == db_models.Group.group_id)
                    .where(db_models.group_user.user_id == user.user_id)
                    .order_by(db_models.Group.group_id))
        
        found_group = session.exec(statement).all()
        return found_group
    
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
                    500:{'description':'error interno', 'model':responses.DatabaseErrorResponse}
            })
def append_user_group(  group_id: int,
                        user_id: int,
                        user: db_models.User = Depends(auth_user),
                        session: Session = Depends(get_session)):

    try:
        is_admin_in_group(user, group_id, session)

        found_group = get_group_or_404(group_id, session)
        
        # Busca el usuario
        new_user = get_user_or_404(user_id, session)

        if new_user in found_group.users:
            logger.error(f'El user {user_id} ya existe en el grupo {group_id}')
            raise exceptions.UserInGroupError(user_id=new_user.user_id, group_id=found_group.group_id)
        
        # Lo agrega al grupo
        found_group.users.append(new_user)
        session.commit()        
        return {'detail':'El usuario ha sido agregado al grupo'}
    
    except SQLAlchemyError as e:
        logger.error(f'Error al agregar un usuario al grupo {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='append_user_group')

@router.delete(
            '/{group_id}/{user_id}',
            description='Permite al usuario autenticado con rol Administrador el eliminar un usuario del grupo',
            responses={
                    200:{'description':'Usuario eliminado del Grupo', 'model':responses.GroupDeleteUserSucces},
                    400:{'description':'request error', 'model':responses.ErrorInRequest},
                    401:{'description':'Usuario no autorizado', 'model':responses.NotAuthorized},
                    404:{'description':'Grupo no encontrado', 'model':responses.NotFound},
                    500:{'description':'error interno', 'model':responses.DatabaseErrorResponse}
            })
def delete_user_group(  group_id: int,
                        user_id: int,
                        user: db_models.User = Depends(auth_user),
                        session: Session = Depends(get_session)):

    try:
        is_admin_in_group(user, group_id, session)

        found_group = get_group_or_404(group_id, session)
        
        # Busca el usuario
        found_user = get_user_or_404(user_id, session)

        if found_user in found_group.users:
            # Lo elimina del grupo
            found_group.users.remove(found_user)
            session.commit()
            
            return {'detail':'El usuario ha sido eliminado al grupo'}
        
        else:
            logger.error(f'El user {user_id} no se encontro en el grupo {group_id}')
            raise exceptions.UserNotFoundError(user_id)
    
    except SQLAlchemyError as e:
        logger.error(f'Error al eliminar un usuario del grupo {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='delete_user_group')

@router.patch(  '/{group_id}/{user_id}',
                description='Permite al usuario autenticado con rol Administrador el modificar el rol de un usuario en el grupo',
                responses={
                    200:{'description':'Usuario actualizado en el Grupo', 'model':responses.GroupUPdateUserSucces},
                    400:{'description':'request error', 'model':responses.ErrorInRequest},
                    401:{'description':'Usuario no autorizado', 'model':responses.NotAuthorized},
                    404:{'description':'Grupo no encontrado', 'model':responses.NotFound},
                    500:{'description':'error interno', 'model':responses.DatabaseErrorResponse}
            })
def update_user_group(  group_id: int,
                        user_id: int,
                        update_role: schemas.UpdateRoleUser,
                        user: db_models.User = Depends(auth_user),
                        session: Session = Depends(get_session)):

    try:
        is_admin_in_group(user, group_id, session)

        get_group_or_404(group_id, session)

        # Busca el usuario
        statement = (select(db_models.group_user)
                    .join(db_models.Group, db_models.group_user.group_id == db_models.Group.group_id)
                    .where(db_models.group_user.user_id == user_id))

        found_user = session.exec(statement).first()

        if not found_user:
            logger.error(f'No se encontro el user {user_id} en el grupo {group_id}')
            raise exceptions.UserNotInGroupError(user_id=user_id, group_id=group_id)

        found_user.role = update_role.role
        
        session.commit()

        return {'detail':'Se ha cambiado los permisos del usuario en el grupo'}
    
    except SQLAlchemyError as e:
        logger.error(f'Error al actualizar el usuario en el grupo')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='update_user_group')

@router.get('/{group_id}/users',
            description='Obtiene todos los usuarios de un grupo',
            responses={
                    200:{'description':'Usuarios del Grupo obtenidos', 'model':schemas.ReadGroupUser},
                    404:{'description':'Grupo no encontrado', 'model':responses.NotFound},
                    500:{'description':'error interno', 'model':responses.DatabaseErrorResponse}
            })
def get_user_in_group(
                    group_id: int,
                    session:Session = Depends(get_session)) -> List[schemas.ReadGroupUser]:

    try:
        get_group_or_404(group_id, session)
        
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
        logger.error(f'Error al obtener los usuarios del grupo {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='get_user_in_group')