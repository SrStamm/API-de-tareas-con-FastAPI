from fastapi import APIRouter, status, HTTPException, Depends
from models import db_models, schemas
from db.database import get_session, Session, select, SQLAlchemyError
from typing import List

router = APIRouter(tags=['Project'])

@router.get('/{group_id}/project')
def get_projects(group_id: int,
                 session:Session = Depends(get_session)) -> List[schemas.ReadProject]:
    try:
        statement = select(db_models.Project).where(db_models.Project.group_id == group_id)
        found_projects = session.exec(statement).all()
        return found_projects
    
    except SQLAlchemyError as e:
        raise {'error en get_projects': f'error {e}'}

@router.post('/{group_id}/project')
def create_group( new_project: schemas.CreateProject,
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
    
@router.patch('/{group_id}/{project_id}')
def update_group(group_id: int,
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
    

@router.delete('/{group_id}/{project_id}')
def delete_group(group_id: int,
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