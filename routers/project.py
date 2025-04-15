from fastapi import APIRouter, status, HTTPException, Depends
from models import db_models, schemas
from db.database import get_session, Session, select, SQLAlchemyError
from typing import List

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
def create_project( new_project: schemas.CreateProject,
                  group_id: int,
                  session:Session = Depends(get_session)):
    try:
        statement = select(db_models.Group).where(db_models.Group.group_id == group_id)
        founded_group = session.exec(statement).first()

        if not founded_group:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='No se encontro el grupo')

        new_project = db_models.Project(**new_project.model_dump(), group_id=founded_group.group_id)
        
        session.add(new_project)
        session.commit()

        return {'detail':'Se ha creado un nuevo proyecto de forma exitosa'}
    except SQLAlchemyError as e:
        raise {'error en create_project':f'error {e}'}

@router.patch('/{group_id}/{project_id}', description='Modifica un proyecto de un grupo')
def update_project(group_id: int,
                 project_id: int,
                 updated_project: schemas.UpdateProject,
                 session: Session = Depends(get_session)): 

    try:
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
        raise {'error en update_project':f'error {e}'}

@router.delete('/{group_id}/{project_id}', description='Elimina un proyecto de un grupo')
def delete_project(group_id: int,
                 project_id: int,
                 session: Session = Depends(get_session)):

    try:
        statement = select(db_models.Project).where(db_models.Project.group_id == group_id, db_models.Project.project_id == project_id)
        founded_project = session.exec(statement).first()
        
        if not founded_project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el proyecto')
        
        session.delete(founded_project)
        session.commit()
        
        return {'detail':'Se ha eliminado el proyecto'}
    
    except SQLAlchemyError as e:
        raise {'error en delete_project':f'error {e}'}


@router.post('/{group_id}/{project_id}/{user_id}', description='Agrega un usuario al proyecto')
def append_user_project(group_id: int,
                        user_id: int,
                        project_id: int,
                        session: Session = Depends(get_session)):

    try:
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
        raise {'error en append_user_project':f'error {e}'}

@router.delete('/{group_id}/{project_id}/{user_id}', description='Elimina un usuario del proyecto')
def delete_user_project(group_id: int,
                        project_id: int,
                        user_id: int,
                        session: Session = Depends(get_session)):

    try:
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
        raise {'error en delete_user_project':f'error {e}'}