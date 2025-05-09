from fastapi import APIRouter, Depends, Request
from models import db_models, schemas, exceptions, responses
from db.database import get_session, Session, select, selectinload, SQLAlchemyError
from typing import List
from .auth import auth_user
from utils import get_group_or_404, get_user_or_404, found_project_or_404, require_permission
from core.logger import logger
from core.limiter import limiter

router = APIRouter(prefix='/project', tags=['Project'])

@router.get(
        '/me',
        description="""  Obtiene todos los proyectos existentes donde el usuario es miembro de este.
                    'skip' recibe un int que saltea el resultado obtenido.
                    'limit' recibe un int para limitar los resultados obtenidos.""",
        responses={
            200:{'description':'Projectos donde esta el usuario obtenidos', 'model':schemas.ReadBasicProject},
            500:{'description':'error interno','model':responses.DatabaseErrorResponse}})
@limiter.limit("10/minute")
def get_projects_iam(
        request:Request,
        limit:int = 10,
        skip: int = 0,
        user: db_models.User = Depends(auth_user),
        session: Session = Depends(get_session)) -> List[schemas.ReadBasicProject]:

    try:
        statement = (select(db_models.Project.project_id, db_models.Project.group_id, db_models.Project.title)
                    .where( db_models.Project.project_id == db_models.project_user.project_id,
                            db_models.project_user.user_id == user.user_id)
                    .limit(limit).offset(skip))
        
        found_projects = session.exec(statement).all()
        return found_projects

    except SQLAlchemyError as e:
        logger.error(f'Error al obtener los proyectos a los que pertenece el user {user.user_id}: {e}')
        raise exceptions.DatabaseError(error=e, func='get_projects_iam')

@router.get(
        '/{group_id}',
        description=""" Obtiene todos los proyectos existentes de un grupo.
                        'skip' recibe un int que saltea el resultado obtenido.
                        'limit' recibe un int para limitar los resultados obtenidos.""",
        responses={
            200:{'description':'Projectos de un grupo obtenidos', 'model':schemas.ReadProject},
            404:{'description':'Grupo o proyectos no encontrados','model':responses.NotFound},
            500:{'description':'error interno','model':responses.DatabaseErrorResponse}})
@limiter.limit("20/minute")
def get_projects(
        request:Request,
        group_id: int,
        limit:int = 10,
        skip: int = 0,
        user: db_models.User = Depends(auth_user),
        session: Session = Depends(get_session)) -> List[schemas.ReadProject]:

    try:
        get_group_or_404(group_id=group_id, session=session)
        

        statement = (select(db_models.Project)
                    .options(selectinload(db_models.Project.users))
                    .where(db_models.Project.group_id == group_id)
                    .limit(limit).offset(skip))
        
        found_projects = session.exec(statement).all()
        return found_projects
    
    except SQLAlchemyError as e:
        logger.error(f'Error al obtener todos los proyectos del grupo {group_id}: {e}')
        raise exceptions.DatabaseError(error=e, func='get_projects')

@router.post(
        '/{group_id}',
        description= """Permite crear un nuevo proyecto en un grupo al usuario autenticado.
                        Para crearlo se necesita un 'title', opcional 'description'""",
        responses={
            200:{'description':'Projecto creado', 'model':responses.ProjectCreateSucces},
            404:{'description':'Grupo no encontrado','model':responses.NotFound},
            500:{'description':'error interno','model':responses.DatabaseErrorResponse}})
@limiter.limit("10/minute")
def create_project(
        request:Request,
        new_project: schemas.CreateProject,
        group_id: int,
        user: db_models.User = Depends(auth_user),
        session:Session = Depends(get_session)):
    try:
        found_group = get_group_or_404(group_id, session)

        project = db_models.Project(**new_project.model_dump(), group_id=found_group.group_id)
        
        session.add(project)
        session.commit()
        session.refresh(project)

        # Agregar al usuario creador al grupo con el rol de administrador
        project_user = db_models.project_user(
            project_id=project.project_id,
            user_id=user.user_id,
            permission=db_models.Project_Permission.ADMIN
        )
        session.add(project_user)

        statement = (select(db_models.group_user).where(db_models.group_user.group_id == group_id))
        users_in_group = session.exec(statement).all()

        if users_in_group:
            for group_id, user_id, role in users_in_group:
                if role == db_models.Group_Role.ADMIN:
                    
                    project_user = db_models.project_user(
                    project_id=project.project_id,
                    user_id=user_id,
                    permission=db_models.Project_Permission.ADMIN
                    )
                session.add(project_user)

        session.commit()

        return {'detail':'Se ha creado un nuevo proyecto de forma exitosa'}
    
    except SQLAlchemyError as e:
        logger.error(f'Error al crear un proyecto en el grupo {group_id}: {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='create_project')

@router.patch(
        '/{group_id}/{project_id}',
        description= """ Permite modificar un proyecto de un grupo si tiene permiso de Administrador en el proyecto.
                        Se puede modificar 'title' y 'description' """,
        responses={
            200:{'description':'Projecto actualizado', 'model':responses.ProjectUpdateSucces},
            401:{'description':'El usuario no esta autorizado','model':responses.NotAuthorized},
            404:{'description':'Grupo o proyecto no encontrados','model':responses.NotFound},
            500:{'description':'error interno','model':responses.DatabaseErrorResponse}})
@limiter.limit("15/minute")
def update_project(
        request:Request,
        group_id: int,
        project_id: int,
        updated_project: schemas.UpdateProject,
        auth_data: dict = Depends(require_permission(permissions=['admin'])),
        session: Session = Depends(get_session)):  

    try:
        found_project = found_project_or_404(group_id=group_id, project_id=project_id, session=session)
                
        if found_project.title != updated_project.title and updated_project.title is not None:
            found_project.title = updated_project.title
            
        if found_project.description != updated_project.description and updated_project.description is not None:
            found_project.description = updated_project.description
        
        session.commit()
        
        return {'detail':'Se ha actualizado la informacion del projecto'}
    
    except SQLAlchemyError as e:
        logger.error(f'Error al actualizar el proyecto {project_id} en el grupo {group_id}: {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='update_project')

@router.delete(
        '/{group_id}/{project_id}',
        description="""Permite eliminar un proyecto de un grupo si el usuario autenticado tiene permiso de Administrador en el proyecto""",
        responses={
            200:{'description':'Projecto eliminado', 'model':responses.ProjectDeleteSucces},
            401:{'description':'El usuario no esta autorizado','model':responses.NotAuthorized},
            404:{'description':'Grupo o proyecto no encontrados','model':responses.NotFound},
            500:{'description':'error interno','model':responses.DatabaseErrorResponse}})
@limiter.limit("5/minute")
def delete_project(
        request:Request,
        group_id: int,
        project_id: int,
        auth_data: dict = Depends(require_permission(permissions=['admin'])),
        session: Session = Depends(get_session)):

    try:
        found_project = found_project_or_404(group_id=group_id, project_id=project_id, session=session)
        
        session.delete(found_project)
        session.commit()
        
        return {'detail':'Se ha eliminado el proyecto'}
    
    except SQLAlchemyError as e:
        logger.error(f'Error al eliminar el proyecto {project_id} en el grupo {group_id}: {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='delete_project')

@router.post(
        '/{group_id}/{project_id}/{user_id}',
        description= """ Permite al usuario autenticado con permiso de Administrador
                        el agregar un usuario al proyecto si este existe en el grupo.""",
        responses={
            200:{'description':'Usuario agregado al projecto', 'model':responses.ProjectAppendUserSucces},
            400:{'description':'Error en request', 'model':responses.ErrorInRequest},
            401:{'description':'El usuario no esta autorizado','model':responses.NotAuthorized},
            404:{'description':'Grupo o proyecto no encontrados','model':responses.NotFound},
            500:{'description':'error interno','model':responses.DatabaseErrorResponse}})
@limiter.limit("10/minute")
def add_user_to_project(
        request:Request,
        group_id: int,
        user_id: int,
        project_id: int,
        auth_data: dict = Depends(require_permission(permissions=['admin'])),
        session: Session = Depends(get_session)):

    try:
        found_project = found_project_or_404(group_id, project_id, session)
        
        # Busca el usuario
        user = get_user_or_404(user_id=user_id, session=session) 

        # Busca el grupo y verifica si el usuario existe en este
        group = get_group_or_404(group_id=group_id, session=session)

        if not user in group.users:
            logger.error(f'El user {user_id} no existe en el grupo {group_id}')
            raise exceptions.UserNotInGroupError(user_id=user_id, group_id=group_id)

        if user in found_project.users:
            logger.error(f'El user {user_id} ya existe en el proyecto {project_id}')
            raise exceptions.UserInProjectError(user_id=user_id, project_id=project_id)
        
        # Lo agrega al grupo
        found_project.users.append(user)
        
        session.commit()
        
        return {'detail':'El usuario ha sido agregado al proyecto'}
    
    except SQLAlchemyError as e:
        logger.error(f'Error al agregar al user {user_id} al proyecto {project_id}: {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='add_user_to_project')

@router.delete(
        '/{group_id}/{project_id}/{user_id}',
        description="""Permite al usuario autenticado con permiso de Administrador
                        el eliminar un usuario del proyecto""",
        responses={
            200:{'description':'Usuario eliminado del projecto', 'model':responses.ProjectDeleteUserSucces},
            400:{'description':'Error en request', 'model':responses.ErrorInRequest},
            401:{'description':'El usuario no esta autorizado','model':responses.NotAuthorized},
            404:{'description':'Grupo o proyecto no encontrados','model':responses.NotFound},
            500:{'description':'error interno','model':responses.DatabaseErrorResponse}})
@limiter.limit("10/minute")
def remove_user_from_project(
        request:Request,
        group_id: int,
        project_id: int,
        user_id: int,
        auth_data: dict = Depends(require_permission(permissions=['admin'])),
        session: Session = Depends(get_session)):

    try:
        found_project = found_project_or_404(group_id, project_id, session)
        
        # Busca el usuario
        user = get_user_or_404(user_id=user_id, session=session)

        # Busca el grupo y verifica si el usuario existe en este
        group = get_group_or_404(group_id=group_id, session=session)
        
        if not user in group.users:
            logger.error(f'El user {user_id} no existe en el grupo {group_id}')
            raise exceptions.UserNotInGroupError(user_id=user_id, group_id=group_id)

        if user in found_project.users:
            # Lo elimina del proyecto
            found_project.users.remove(user)
            session.commit()
            
            return {'detail':'El usuario ha sido eliminado del proyecto'}
        else:
            logger.error(f'El user {user_id} no existe en el proyecto {project_id}')
            raise exceptions.UserNotInProjectError(user_id=user_id, project_id=project_id)
    
    except SQLAlchemyError as e:
        logger.error(f'Error al remover al user {user_id} del proyecto {project_id}: {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='remove_user_from_project')

@router.patch(
        '/{group_id}/{project_id}/{user_id}',
        description= """Permite al usuario autenticado con permiso de Administrador
                        el modificar el rol de un usuario en un proyecto""",
        responses={
            200:{'description':'Permisos del usuario sobre el projecto actualizado', 'model':responses.ProjectUPdateUserSucces},
            400:{'description':'Error en request', 'model':responses.ErrorInRequest},
            401:{'description':'El usuario no esta autorizado','model':responses.NotAuthorized},
            404:{'description':'Grupo o proyecto no encontrados','model':responses.NotFound},
            500:{'description':'error interno','model':responses.DatabaseErrorResponse}})
@limiter.limit("15/minute")
def update_user_permission_in_project(
        request:Request,
        group_id: int,
        user_id: int,
        project_id: int,
        update_role: schemas.UpdatePermissionUser,
        auth_data: dict = Depends(require_permission(permissions=['admin'])),
        session: Session = Depends(get_session)):

    try:
        project = found_project_or_404(group_id, project_id, session)

        # Busca el usuario
        statement = (select(db_models.project_user)
                    .where(db_models.project_user.user_id == user_id, db_models.project_user.project_id == project.project_id))

        user = session.exec(statement).first()

        if not user:
            logger.error(f'El user {user_id} no existe en el proyecto {project_id}')
            raise exceptions.UserNotInProjectError(project_id=project_id, user_id=user_id)

        user.permission = update_role.permission
        
        session.commit()

        return {'detail':'Se ha cambiado los permisos del usuario en el proyecto'}
    
    except SQLAlchemyError as e:
        logger.error(f'Error al actualizar permisos del user {user_id} del proyecto {project_id}: {e}')
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='update_user_permission_in_project')

@router.get(
        '/{group_id}/{project_id}/users',
        description=""" Obtiene todos los usuarios de un proyecto.
                    'skip' recibe un int que saltea el resultado obtenido.
                    'limit' recibe un int para limitar los resultados obtenidos.""",
        responses={
                200:{'description':'Usuarios del proyecto obtenidos', 'model':schemas.ReadProjectUser},
                400:{'description':'Error en request', 'model':responses.ErrorInRequest},
                404:{'description':'Grupo o proyecto no encontrados','model':responses.NotFound},
                500:{'description':'error interno','model':responses.DatabaseErrorResponse}})
@limiter.limit("20/minute")
def get_user_in_project(
        request:Request,
        group_id: int,
        project_id: int,
        limit:int = 10,
        skip: int = 0,
        session:Session = Depends(get_session),
        user: db_models.User = Depends(auth_user)) -> List[schemas.ReadProjectUser]:
    try:
        found_project_or_404(group_id, project_id, session)

        statement = (select(db_models.User.user_id, db_models.User.username, db_models.project_user.permission)
                    .join(db_models.project_user, db_models.project_user.user_id == db_models.User.user_id)
                    .where(db_models.project_user.project_id == project_id)
                    .limit(limit).offset(skip))
        
        results = session.exec(statement).all()

        if not results:
            logger.error(f'No se encontraron los usuarios en el proyecto {project_id}')
            raise exceptions.UsersNotFoundInProjectError(project_id=project_id)
        
        # El resultado son tuplas, entonces se debe hacer lo siguiente para que devuelva la informacion solicitada
        return [
            schemas.ReadProjectUser(user_id=user_id, username=username, permission=permission)
            for user_id, username, permission in results
        ]

    except SQLAlchemyError as e:
        logger.error(f'Error al obtener los usuarios del proyecto {project_id}: {e}')
        raise exceptions.DatabaseError(error=e, func='get_user_in_project')