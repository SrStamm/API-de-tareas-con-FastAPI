from fastapi import APIRouter, status, HTTPException, Depends
from models import db_models, schemas
from .auth import auth_user
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
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'error en get_task: {str(e)}')

@router.get('/{project_id}', description='Obtiene todas las tareas asignadas de un proyecto')
def get_task_in_project(project_id: int,
                        user: db_models.User = Depends(auth_user),
                        session: Session = Depends(get_session)) -> List[schemas.ReadTask]:
    try:
        # Selecciona las tareas asignadas a los usuarios en el proyecto
        statement = (select(db_models.Task)
                     .join(db_models.tasks_user, db_models.tasks_user.task_id == db_models.Task.task_id)
                     .join(db_models.project_user, db_models.project_user.user_id == db_models.tasks_user.user_id)
                     .where(db_models.project_user.project_id == project_id, db_models.project_user.user_id == user.user_id))
        
        found_tasks = session.exec(statement).all()
        return found_tasks
    
    except SQLAlchemyError as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'error en get_task_in_project: {str(e)}')
    
@router.post('/{project_id}', description='Crea una nueva tarea en un proyecto')
def create_task(new_task: schemas.CreateTask,
                project_id: int,
                group_id: int,
                user: db_models.User = Depends(auth_user),
                session: Session = Depends(get_session)):
    try:
        # Verifica que el projecto exista
        statement = select(db_models.Project).where(db_models.Project.project_id == project_id)
        project = session.exec(statement).first()
        if not project:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail='No se encontro el proyecto destinado')
        
        # Verifica que el usuario este autorizado en el proyecto
        statement = (select(db_models.project_user)
                     .where(db_models.project_user.user_id == user.user_id, db_models.project_user.project_id == project_id))
        
        project_user = session.exec(statement).first()

        if not project_user or project_user.permission != db_models.Project_Permission.ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='No tienes permisos')        

        # Busca el usuario al que va a asignarse la tarea, y si existe en el proyecto
        for user_id in new_task.user_ids:
            user_exists = session.get(db_models.User, user_id)
            if not user_exists:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail='No se encontro el usuario')
            
            statement = (select(db_models.project_user).where(
                db_models.project_user.user_id == user_exists.user_id,
                db_models.project_user.project_id == project.project_id))
            
            user_in_project = session.exec(statement).first()
            if not user_in_project:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail='No se encontro el usuario en el proyecto')


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
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f'Error en create_task: {e}')

@router.patch('/{project_id}/{task_id}', description='Actualiza una tarea especifica de un proyecto')
def update_task(task_id: int,
                project_id: int,
                update_task: schemas.UpdateTask,
                session: Session = Depends(get_session)): 

    try:
        # Verifica que exista el proyecto
        project = session.get(db_models.Project, project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro el proyecto')
        
        # Busca la task seleccionada
        statement = select(db_models.Task).where(db_models.Task.task_id == task_id, db_models.Task.project_id == project_id)
        task = session.exec(statement).first()
        
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro la tarea')
        
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
                    raise HTTPException(status.HTTP_404_NOT_FOUND, detail='No se encontro el usuario')

                # Verifica que el usuario exista en el projecto
                statement = (select(db_models.project_user).where(
                    db_models.project_user.user_id == user_exists.user_id,
                    db_models.project_user.project_id == project.project_id))
                
                user_in_project = session.exec(statement).first()
                if not user_in_project:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, detail='No se encontro el usuario en el proyecto')

                # Verifica que el usuario este asignado al task
                statement = (select(db_models.tasks_user).where(
                    db_models.tasks_user.user_id == user_exists.user_id,
                    db_models.tasks_user.task_id == task_id))
                
                user_in_task = session.exec(statement).first()
                if user_in_task:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f'El usuario de id {user_id} no esta asignado a esta tarea')

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
                    raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f'El usuario de id {user_in_task.user_id} no esta asignado a esta tarea')

                session.delete(user_in_task)
        
        session.commit()
        
        return {'detail':'Se ha actualizado la tarea'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'error en update_task: {str(e)}')

@router.delete('/{project_id}/{task_id}', description='Elimina una tarea especifica de un proyecto')
def delete_task(task_id: int,
                project_id: int,
                user: db_models.User = Depends(auth_user),
                session: Session = Depends(get_session)):

    try:
        # Verifica que el usuario tenga permisos
        statement = (select(db_models.project_user).where(
                    db_models.project_user.user_id == user.user_id,
                    db_models.project_user.project_id == project_id))
        
        user_found = session.exec(statement)
        if not user_found or user_found.permission != db_models.Project_Permission.ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail='No tienes la autorizacion para realizar esta accion')
        
        # Verifica que exista la task
        statement = select(db_models.Task).where(db_models.Task.task_id == task_id, db_models.Task.project_id == project_id)
        founded_task = session.exec(statement).first()
        
        if not founded_task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No se encontro la tarea en el proyecto')
        
        session.delete(founded_task)
        session.commit()
        
        return {'detail':'Se ha eliminado la tarea'}
    
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'error en delete_task: {str(e)}')

@router.get('/{project_id}/{task_id}/users', description='Obtiene los usuarios asignados a una tarea')
def get_tasks_for_users(task_id: int,
                        project_id: int,
                        session: Session = Depends(get_session)) -> List[schemas.ReadUser]:
    try:
        statement = (select(db_models.User.user_id, db_models.User.username)
                     .join(db_models.tasks_user, db_models.tasks_user.user_id == db_models.User.user_id)
                     .where(db_models.tasks_user.task_id == task_id))

        resultados = session.exec(statement).all()

        return resultados

    except SQLAlchemyError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f'Error en get_tasks_for_users: {e}')