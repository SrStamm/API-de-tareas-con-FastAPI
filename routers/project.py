from fastapi import APIRouter, status, HTTPException, Depends
from models import db_models, schemas
from db.database import get_session, Session, select, SQLAlchemyError
from typing import List
from .auth import auth_user

router = APIRouter(prefix='/project', tags=['Project'])


@router.get('/{group_id}', description='Obtiene todos los proyectos de un grupo')
def get_projects(group_id: int, session:Session = Depends(get_session)) -> List[schemas.ReadProject]:

    try:
        statement = select(db_models.Project).where(db_models.Project.group_id == group_id)
        found_projects = session.exec(statement).all()
        return found_projects
    
    except SQLAlchemyError as e:
        raise {'error en get_projects': f'error {e}'}

@router.post('/{group_id}', description='Crea un nuevo proyecto en un grupo')
def create_project(new_project: schemas.CreateProject,
                  group_id: int,
                  user: db_models.User = Depends(auth_user),
                  session:Session = Depends(get_session)):
    try:
        statement = select(db_models.Group).where(db_models.Group.group_id == group_id)
        founded_group = session.exec(statement).first()

        if not founded_group:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='No se encontro el grupo')

        project = db_models.Project(**new_project.model_dump(), group_id=founded_group.group_id)
        
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
        session.commit()

        return {'detail':'Se ha creado un nuevo proyecto de forma exitosa'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f'Error al crear el proyecto: {str(e)}')

@router.patch('/{group_id}/{project_id}', description='Modifica un proyecto de un grupo')
async def update_project(group_id: int,
                 project_id: int,
                 updated_project: schemas.UpdateProject,
                 user: db_models.User = Depends(auth_user),
                 session: Session = Depends(get_session)): 

    try:
        statement = select(db_models.project_user).where(db_models.project_user.user_id == user.user_id, db_models.project_user.project_id == project_id)
        resultado = session.exec(statement).first()

        if not resultado or resultado.permission != 'admin':
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Error: No estas autorizado.')

        statement = select(db_models.Project).where(db_models.Project.group_id == group_id, db_models.Project.project_id == project_id)
        founded_project = session.exec(statement).first()
        
        if not founded_project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el grupo')
        
        if founded_project.title != updated_project.title and updated_project.title is not None:
            founded_project.title = updated_project.title
            
        if founded_project.description != updated_project.description and updated_project.description is not None:
            founded_project.description = updated_project.description
        
        session.commit()
        
        return {'detail':'Se ha actualizado la informacion del projecto'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise {'error en update_project':f'error {e}'}

@router.delete('/{group_id}/{project_id}', description='Elimina un proyecto de un grupo')
def delete_project(group_id: int,
                   project_id: int,
                   user: db_models.User = Depends(auth_user),
                   session: Session = Depends(get_session)):

    try:
        statement = select(db_models.project_user).where(db_models.project_user.user_id == user.user_id, db_models.project_user.project_id == project_id)
        resultado = session.exec(statement).first()

        if not resultado or resultado.permission != 'admin':
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Error: No estas autorizado.')
        
        statement = select(db_models.Project).where(db_models.Project.group_id == group_id, db_models.Project.project_id == project_id)
        founded_project = session.exec(statement).first()
        
        if not founded_project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el proyecto')
        
        session.delete(founded_project)
        session.commit()
        
        return {'detail':'Se ha eliminado el proyecto'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise {'error en delete_project':f'error {e}'}

@router.post('/{group_id}/{project_id}/{user_id}', description='Agrega un usuario al proyecto')
def append_user_project(group_id: int,
                        user_id: int,
                        project_id: int,
                        user: db_models.User = Depends(auth_user),
                        session: Session = Depends(get_session)):

    try:
        # Busca si el usuario tiene permisos para agregar un usario al proyecto
        statement = (select(db_models.project_user)
                     .where(db_models.project_user.user_id == user.user_id, db_models.project_user.project_id == project_id))
        resultado = session.exec(statement).first()

        if not resultado or resultado.permission != 'admin':
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Error: No estas autorizado.')
        
        # Busca el projecto actual
        statement = (select(db_models.Project)
                     .where(db_models.Project.group_id == group_id, db_models.Project.project_id == project_id))
        
        founded_project = session.exec(statement).first()

        if not founded_project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No existe o no se encontro el proyecto')
        
        # Busca el usuario
        user = session.get(db_models.User, user_id)

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el usuario')

        # Busca el grupo y verifica si el usuario existe en este
        group = session.get(db_models.Group, group_id)

        if not user in group.users:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='El usuario no existe en el grupo')

        if user in founded_project.users:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='El usuario ya existe en el proyecto')
        
        # Lo agrega al grupo
        founded_project.users.append(user)
        
        session.commit()
        
        return {'detail':'El usuario ha sido agregado al proyecto'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise {'error en append_user_project':f'error {e}'}

@router.delete('/{group_id}/{project_id}/{user_id}', description='Elimina un usuario del proyecto')
def delete_user_project(group_id: int,
                        project_id: int,
                        user_id: int,
                        user: db_models.User = Depends(auth_user),
                        session: Session = Depends(get_session)):

    try:
        statement = select(db_models.project_user).where(db_models.project_user.user_id == user.user_id, db_models.project_user.project_id == project_id)
        resultado = session.exec(statement).first()

        if not resultado or resultado.permission != 'admin':
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Error: No estas autorizado.')
        
        statement = (select(db_models.Project)
                    .where(db_models.Project.group_id == group_id, db_models.Project.project_id == project_id))
        
        founded_project = session.exec(statement).first()

        if not founded_project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No existe o no se encontro el proyecto')
        
        # Busca el usuario
        user = session.get(db_models.User, user_id)

        # Busca el grupo y verifica si el usuario existe en este
        group = session.get(db_models.Group, group_id)        
        
        if not user in group.users:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='El usuario no existe en el grupo')

        if not founded_project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el usuario')

        if user in founded_project.users:
            # Lo elimina del proyecto
            founded_project.users.remove(user)
            session.commit()
            
            return {'detail':'El usuario ha sido eliminado del proyecto'}
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='El usuario no esta en el proyecto')
    
    except SQLAlchemyError as e:
        session.rollback()
        raise {'error en delete_user_project':f'error {e}'}

@router.patch('/{group_id}/{project_id}/{user_id}', description='Modifica el rol de un usuario en un proyecto')
def update_user_project(group_id: int,
                        user_id: int,
                        project_id: int,
                        update_role: schemas.UpdatePermissionUser,
                        user: db_models.User = Depends(auth_user),
                        session: Session = Depends(get_session)):

    try:
        statement = select(db_models.project_user).where(db_models.project_user.user_id == user.user_id, db_models.project_user.project_id == project_id)
        resultado = session.exec(statement).first()

        if not resultado or resultado.permission != 'admin':
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Error: No estas autorizado.')
        
        # Verifica que exista el proyecto
        statement = select(db_models.Project).where(db_models.Project.group_id == group_id, db_models.Project.project_id == project_id)
        project = session.exec(statement).first()

        if project is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='No se encontro el proyecto')
                
        # Busca el usuario
        statement = (select(db_models.project_user)
                     .where(db_models.project_user.user_id == user_id, db_models.project_user.project_id == project_id))

        user = session.exec(statement).first()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el usuario')

        user.permission = update_role.permission
        
        session.commit()

        return {'detail':'Se ha cambiado los permisos del usuario en el proyecto'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise {'error en append_user_project':f'error {e}'}

@router.get('/{group_id}/{project_id}/users', description='Obtiene todos los grupos')
def get_user_in_project(group_id: int,
                      project_id: int,
                      session:Session = Depends(get_session)
                    ) -> List[schemas.ReadProjectUser]:
    try:
        statement = select(db_models.Project).where(db_models.Project.group_id == group_id, db_models.Project.project_id == project_id)
        
        project = session.exec(statement).first()

        if project is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='No se encontro el proyecto')

        statement = (select(db_models.User, db_models.project_user.permission)
                    .join(db_models.project_user, db_models.project_user.user_id == db_models.User.user_id)
                    .where(db_models.project_user.project_id == project_id))
        
        results = session.exec(statement).all()

        if not results:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='No se encontraron los usuarios pertenecientes al proyecto')
        
        # El resultado son tuplas, entonces se debe hacer lo siguiente para que devuelva la informacion solicitada
        return [
            schemas.ReadProjectUser(user_id=user.user_id, username=user.username, permission=permission)
            for user, permission in results
        ]

    except SQLAlchemyError as e:
        raise {'Error en get_user_in_project':f'error {e}'}
    
@router.get('/{group_id}/{project_id}/tasks', description='Obtiene todos los grupos')
def get_user_in_project(group_id: int,
                        project_id: int,
                        session:Session = Depends(get_session)):
    try:
        statement = (
            select(
                db_models.Task.task_id,
                db_models.Task.description,
                db_models.Task.state,
                db_models.User.user_id,
                db_models.User.username
            )
            .join(db_models.tasks_user, db_models.tasks_user.task_id == db_models.Task.task_id)
            .join(db_models.User, db_models.tasks_user.user_id == db_models.User.user_id)
            .where(db_models.Task.project_id == project_id)
        )
        
        project = session.exec(statement).all()

        if project is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='No se encontro el proyecto')

        return project

    except SQLAlchemyError as e:
        raise {'Error en get_user_in_project':f'error {e}'}