from fastapi import APIRouter, status, HTTPException, Depends
from models import db_models, schemas
from db.database import get_session, Session, select, SQLAlchemyError, or_
from typing import List

router = APIRouter(prefix='/task', tags=['Task'])

@router.get('', description='Obtiene todas las tareas')
def get_task(session:Session = Depends(get_session)) -> List[schemas.ReadTask]:
    try:
        statement = select(db_models.Task)
        found_tasks = session.exec(statement).all()
        return found_tasks
    
    except SQLAlchemyError as e:
        raise {'error en get_task': f'error {e}'}

@router.post('/{project_id}/{user_id}', description='Crea una nueva tarea en un proyecto')
def create_task(new_task: schemas.CreateTask,
                project_id: int,
                user_id: int,
                session: Session = Depends(get_session)):
    try:
        statement = select(db_models.Project).where(db_models.Project.project_id == project_id)
        founded_project = session.exec(statement).first()

        if not founded_project:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='No se encontro el proyecto destinado')

        new_task = db_models.Task(**new_task.model_dump(), project_id=founded_project.project_id)

        user = session.get(db_models.User, user_id)

        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='No se encontro el usuario')

        session.add(new_task)
        session.commit()
        session.refresh(new_task)

        asigned = db_models.tasks_user( task_id=new_task.task_id,
                                        user_id=user_id)

        session.add(asigned)
        session.commit()

        return {'detail':'Se ha creado una nueva tarea con exito'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f'Error {e}')

@router.post('/{project_id}/{task_id}')
def asing_user_in_task(task_id: int,
                       users: schemas.AsignUser,
                       session: Session = Depends(get_session)):
    try:
        task = session.get(db_models.Task, task_id)

        if not task:
            raise

        for user in users:
            user_asigned = db_models.tasks_user(task_id=task_id, user_id=user.users)
            session.add(user_asigned)
        
        session.commit()

    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f'Error {e}')

@router.patch('/{project_id}/{task_id}', description='Actualiza una tarea especifica de un proyecto')
def update_task(task_id: int,
                project_id: int,
                updated_task: schemas.UpdateTask,
                session: Session = Depends(get_session)): 

    try:
        statement = select(db_models.Task).where(db_models.Task.task_id == task_id, db_models.Task.project_id == project_id)
        founded_task = session.exec(statement).first()
        
        if not founded_task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro la tarea')
        
        if founded_task.description != updated_task.description and updated_task.description:
            founded_task.description = updated_task.description

        if founded_task.date_exp != updated_task.date_exp and updated_task.date_exp:
            founded_task.date_exp = updated_task.date_exp
            
        if founded_task.state != updated_task.state and updated_task.state:
            founded_task.state = updated_task.state
        
        session.commit()
        
        return {'detail':'Se ha actualizado la tarea'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise {'error en update_task':f'error {e}'}

@router.delete('/{project_id}/{task_id}', description='Elimina una tarea especifica de un proyecto')
def delete_task(task_id: int,
                project_id: int,
                session: Session = Depends(get_session)):

    try:
        statement = select(db_models.Task).where(db_models.Task.task_id == task_id, db_models.Task.project_id == project_id)
        founded_task = session.exec(statement).first()
        
        if not founded_task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro la tarea en el proyecto')
        
        session.delete(founded_task)
        session.commit()
        
        return {'detail':'Se ha eliminado la tarea'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise {'error en delete_task':f'error {e}'}

@router.get('/{task_id}/users', description='Obtiene los usuarios asignados a una tarea')
def get_tasks_for_users(task_id: int,
                        session: Session = Depends(get_session)) -> List[schemas.ReadUser]:
    try:
        statement = (select(db_models.User.user_id, db_models.User.username)
                     .join(db_models.tasks_user, db_models.tasks_user.user_id == db_models.User.user_id)
                     .where(db_models.tasks_user.task_id == task_id))
        
        resultados = session.exec(statement).all()

        return resultados

    except SQLAlchemyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Error en get_tasks_for_users: {e}')