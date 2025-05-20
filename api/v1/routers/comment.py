from fastapi import APIRouter, Depends, Request
from models import db_models, schemas, exceptions
from .auth import auth_user
from db.database import get_session, Session, select, SQLAlchemyError
from typing import List
from core.utils import found_user_in_task_or_404, extract_valid_mentions, notify_users, validate_in_task
from core.logger import logger
from core.limiter import limiter

router = APIRouter(prefix='/task/{task_id}', tags=['Comment'])

@router.get('/comments')
@limiter.limit("100/minute")
def get_comments(
        request:Request,
        task_id:int,
        user: db_models.User = Depends(auth_user),
        session:Session = Depends(get_session)) -> List[schemas.ReadComment]:
    try:
        found_user_in_task_or_404(user.user_id, task_id, session)

        stmt = (select(db_models.Task_comments)
                .where(
                    db_models.Task_comments.task_id == task_id,
                    db_models.Task_comments.is_deleted == False
                    ))

        comments_found = session.exec(stmt).all()

        if not comments_found:
            logger.error(f'Comentarios no encontrados en {task_id}')
            raise exceptions.CommentNotFoundError(task_id)

        return comments_found

    except SQLAlchemyError as e:
        logger.error(f'Error interno: {e}')
        raise exceptions.DatabaseError(e, func='get_comments')

@router.get('/comments/all')
@limiter.limit("100/minute")
def get_all_comments(
        request:Request,
        task_id:int,
        user: db_models.User = Depends(auth_user),
        session:Session = Depends(get_session)) -> List[schemas.ReadComment]:
    try:
        found_user_in_task_or_404(user.user_id, task_id, session)

        stmt = (select(db_models.Task_comments)
                .where(db_models.Task_comments.task_id == task_id))

        comments_found = session.exec(stmt).all()

        if not comments_found:
            logger.error(f'Comentarios no encontrados en {task_id}')
            raise exceptions.CommentNotFoundError(task_id)

        return comments_found

    except SQLAlchemyError as e:
        logger.error('Error interno: {e}')
        raise exceptions.DatabaseError(e, func='get_comments')

@router.post('/comments')
@limiter.limit("30/minute")
async def create_comment(
        request:Request,
        task_id:int,
        new_comment:schemas.CreateComment,
        user: db_models.User = Depends(auth_user),
        session:Session = Depends(get_session)):
    try:
        found_user_in_task_or_404(user.user_id, task_id, session)

        add_comment = db_models.Task_comments(
            content=new_comment.content,
            user_id=user.user_id,
            task_id=task_id)

        session.add(add_comment)
        session.commit()
        session.refresh(add_comment)

        found_users = extract_valid_mentions(add_comment.content, session)

        if found_users:
            users_validated = validate_in_task(found_users, task_id, session)
            
            if users_validated: 
                payload = schemas.NotificationPayload(
                    notification_type='task_mention',
                    message=f'User {user.user_id} mentionated on comments in Task {task_id}: {add_comment.content}')

                await notify_users(users_validated, payload)
                logger.info(f'Notificacion enviada: {payload}')

        return {'detail':'Nuevo comentario creado'}

    except SQLAlchemyError as e:
        logger.error('Error interno: {e}')
        raise exceptions.DatabaseError(e, func='create_comment')

@router.patch('/comments/{comment_id}')
@limiter.limit("30/minute")
def update_comment(
        request:Request,
        task_id:int,
        comment_id:int,
        update_comment:schemas.UpdateComment,
        user: db_models.User = Depends(auth_user),
        session:Session = Depends(get_session)):
    try:
        found_user_in_task_or_404(user.user_id, task_id, session)

        comment_found = session.get(db_models.Task_comments, comment_id)

        if not comment_found:
            logger.error(f'Comentario no encontrado en {task_id}')
            raise exceptions.CommentNotFoundError(task_id)

        if comment_found.user_id != user.user_id:
            logger.error(f'User {user.user_id} no autorizado')
            raise exceptions.UserNotAuthorizedInCommentError(user.user_id, comment_id)

        if update_comment.content:
            comment_found.content = update_comment.content

        # Actualizando la fecha
        comment_found.update_at = update_comment.update_at

        session.commit()

        return {'detail':'Comentario actualizado'}

    except SQLAlchemyError as e:
        logger.error('Error interno: {e}')
        raise exceptions.DatabaseError(e, func='update_comment')

@router.delete('/comments/{comment_id}')
@limiter.limit("30/minute")
def delete_comment(
        request:Request,
        task_id:int,
        comment_id:int,
        user: db_models.User = Depends(auth_user),
        session:Session = Depends(get_session)):
    try:
        found_user_in_task_or_404(user.user_id, task_id, session)

        comment_found = session.get(db_models.Task_comments, comment_id)

        if not comment_found:
            logger.error(f'Comentario no encontrado en {task_id}')
            raise exceptions.CommentNotFoundError(task_id)

        if comment_found.user_id != user.user_id:
            logger.error(f'User {user.user_id} no autorizado')
            raise exceptions.UserNotAuthorizedInCommentError(user.user_id, comment_id)

        # Actualizando el estado
        comment_found.is_deleted = True

        session.commit()

        return {'detail':'Comentario eliminado'}

    except SQLAlchemyError as e:
        logger.error('Error interno: {e}')
        raise exceptions.DatabaseError(e, func='update_comment')