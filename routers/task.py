from fastapi import APIRouter, status, HTTPException, Depends
from models import db_models, schemas, exceptions
from .auth import auth_user
from .project import is_admin_in_project
from db.database import get_session, Session, select, SQLAlchemyError, or_, joinedload
from typing import List

router = APIRouter(prefix='/task', tags=['Task'])

def found_project_or_404(project_id:int, session: Session):
    stmt = (select(db_models.Project)
            .where(db_models.Project.project_id == project_id))
    
    founded_project = session.exec(stmt).first()
    
    if not founded_project:
        raise exceptions.ProjectNotFoundError(project_id)
    
    return founded_project

def found_task_or_404(project_id:int, task_id: int, session: Session) -> db_models.Task:
    stmt = (select(db_models.Task)
            .where(db_models.Task.project_id == project_id, db_models.Task.task_id == task_id))
    
    task_found = session.exec(stmt).first()
    
    if not task_found:
        raise exceptions.TaskNotFound(task_id=task_id, project_id=project_id)
    
    return task_found

def found_user_or_404(user_id:int, session: Session) -> db_models.User:
    user_found = session.get(db_models.User, user_id)
    
    if not user_found:
        raise exceptions.UserNotFoundError(user_id=user_id)
    
    return user_found

def found_user_in_project_or_404(user_id:int, project_id:int, session: Session) -> db_models.User:
    stmt = (select(db_models.project_user).where(
                    db_models.project_user.user_id == user_id,
                    db_models.project_user.project_id == project_id))
    
    user = session.exec(stmt).first()
    
    if not user:
        raise exceptions.UserNotInProjectError(user_id=user_id, project_id=project_id)
    
    return user

@router.get('', description='Obtiene todas las tareas a las que esta asignada el usuario')
def get_task(user:db_models.User = Depends(auth_user), session:Session = Depends(get_session)) -> List[schemas.ReadTask]:
    try:
        statement = select(db_models.Task).where(db_models.Task.task_id == db_models.tasks_user.task_id, db_models.tasks_user.user_id == user.user_id)
        found_tasks = session.exec(statement).all()
        return found_tasks
    
    except SQLAlchemyError as e:
        raise exceptions.DatabaseError(error=e, func='get_task')

@router.get('/{task_id}/users', description='Obtiene los usuarios asignados a una tarea')
def get_users_for_task(task_id: int,
                        session: Session = Depends(get_session)) -> List[schemas.ReadUser]:
    try:
        statement = (select(db_models.User.user_id, db_models.User.username)
                    .join(db_models.tasks_user, db_models.tasks_user.user_id == db_models.User.user_id)
                    .where(db_models.tasks_user.task_id == task_id))

        resultados = session.exec(statement).all()

        return resultados

    except SQLAlchemyError as e:
        raise exceptions.DatabaseError(error=e, func='get_users_for_task')

@router.get('/{project_id}', description='Obtiene todas las tareas asignadas de un proyecto')
def get_task_in_project(project_id: int,
                        user: db_models.User = Depends(auth_user),
                        session: Session = Depends(get_session)) -> List[schemas.ReadTaskInProject]:
    try:
        # Selecciona las tareas asignadas a los usuarios en el proyecto
        statement = (select(db_models.Task)
                    .join(db_models.tasks_user, db_models.tasks_user.task_id == db_models.Task.task_id)
                    .join(db_models.project_user, db_models.project_user.user_id == db_models.tasks_user.user_id)
                    .where(db_models.project_user.project_id == project_id, db_models.project_user.user_id == user.user_id)
                    .options(joinedload(db_models.Task.asigned)))
        
        found_tasks = session.exec(statement).unique().all()
        return found_tasks
    
    except SQLAlchemyError as e:
        raise exceptions.DatabaseError(error=e, func='get_task_in_project')
    
@router.post('/{project_id}', description='Crea una nueva tarea en un proyecto')
def create_task(new_task: schemas.CreateTask,
                project_id: int,
                user: db_models.User = Depends(auth_user),
                session: Session = Depends(get_session)):
    try:
        # Verifica que el projecto exista
        project = found_project_or_404(project_id=project_id, session=session)
                
        # Verifica que el usuario este autorizado en el proyecto
        is_admin_in_project(user=user, project_id=project_id, session=session)

        # Busca el usuario al que va a asignarse la tarea, y si existe en el proyecto
        if new_task.user_ids:
            for user_id in new_task.user_ids:
                found_user_or_404(user_id=user_id, session=session)
                
                found_user_in_project_or_404(user_id=user_id, project_id=project_id, session=session)

        task = db_models.Task(
            project_id=project_id,
            description=new_task.description,
            date_exp=new_task.date_exp)

        session.add(task)
        session.commit()
        session.refresh(task)

        for user_id in new_task.user_ids:
            task_user = db_models.tasks_user(
                task_id=task.task_id,
                user_id=user_id)
            session.add(task_user)

        session.commit()

        return {'detail':'Se ha creado una nueva tarea y asignado los usuarios con exito'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='create_task')

@router.patch('/{project_id}/{task_id}', description='Actualiza una tarea especifica de un proyecto')
def update_task(task_id: int,
                project_id: int,
                update_task: schemas.UpdateTask,
                session: Session = Depends(get_session)): 

    try:
        # Verifica que exista el proyecto
        project = found_project_or_404(project_id=project_id, session=session)
        
        # Busca la task seleccionada
        task = found_task_or_404(project_id=project_id, task_id=task_id, session=session)
        
        if task.description != update_task.description and update_task.description:
            task.description = update_task.description

        if task.date_exp != update_task.date_exp and update_task.date_exp:
            task.date_exp = update_task.date_exp
            
        if task.state != update_task.state and update_task.state:
            task.state = update_task.state
        
        # Verifica si hay nuevos usuarios a agregar 
        if update_task.append_user_ids:
            for user_id in update_task.append_user_ids:
                # Verifica que el usuario exista
                user_exists = session.get(db_models.User, user_id)
                if not user_exists:
                    raise exceptions.UserNotFoundError(user_id)

                # Verifica que el usuario exista en el projecto
                statement = (select(db_models.project_user).where(
                    db_models.project_user.user_id == user_exists.user_id,
                    db_models.project_user.project_id == project.project_id))
                
                user_in_project = session.exec(statement).first()
                if not user_in_project:
                    raise exceptions.UserNotInProjectError(project_id=project_id, user_id=user_id)

                # Verifica que el usuario este asignado al task
                statement = (select(db_models.tasks_user).where(
                    db_models.tasks_user.user_id == user_exists.user_id,
                    db_models.tasks_user.task_id == task_id))
                
                user_in_task = session.exec(statement).first()
                if user_in_task:
                    raise exceptions.TaskIsAssignedError(user_id=user_id, task_id=task_id)

                # Agrega el usuario al task
                task_user = db_models.tasks_user(
                    task_id=task.task_id,
                    user_id=user_id)
                session.add(task_user)
        

        # Verifica si hay usuarios para eliminar de la tarea 
        if update_task.exclude_user_ids:
            for user_id in update_task.exclude_user_ids:
                # Verifica que el usuario este asignado al task
                statement = (select(db_models.tasks_user).where(
                    db_models.tasks_user.user_id == user_id,
                    db_models.tasks_user.task_id == task_id))
                
                user_in_task = session.exec(statement).first()
                if not user_in_task:
                    raise exceptions.TaskIsNotAssignedError(user_id=user_id, task_id=task_id)

                session.delete(user_in_task)
        
        session.commit()
        
        return {'detail':'Se ha actualizado la tarea'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='update_task')

@router.delete('/{project_id}/{task_id}', description='Elimina una tarea especifica de un proyecto')
def delete_task(task_id: int,
                project_id: int,
                user: db_models.User = Depends(auth_user),
                session: Session = Depends(get_session)):

    try:
        is_admin_in_project(user=user, project_id=project_id, session=session)
        
        # Verifica que exista la task
        task = found_task_or_404(project_id=project_id, task_id=task_id, session=session)
                
        session.delete(task)
        session.commit()
        
        return {'detail':'Se ha eliminado la tarea'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise exceptions.DatabaseError(error=e, func='delete_task')