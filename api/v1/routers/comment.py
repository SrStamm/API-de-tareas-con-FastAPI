from fastapi import APIRouter, Depends, Request
from models import db_models, schemas, exceptions, responses
from .auth import auth_user
from db.database import get_session, Session, select, SQLAlchemyError
from typing import List
from core.utils import found_user_in_task_or_404, extract_valid_mentions, notify_users, validate_in_task
from core.logger import logger
from core.limiter import limiter

router = APIRouter(prefix='/task/{task_id}', tags=['Comment'])

@router.get(
        '/comments',
        description='Read the comments of a specific Task',
        responses={
            200:{'detail':'Comments successfully obtained','model':schemas.ReadComment},
            500:{'detail':'Internal error','model':responses.DatabaseErrorResponse}
        })
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
            logger.error(f'Comments not found in Task {task_id}')
            raise exceptions.CommentNotFoundError(task_id)

        return comments_found

    except SQLAlchemyError as e:
        logger.error(f'Internal error: {e}')
        raise exceptions.DatabaseError(e, func='get_comments')

@router.get(
        '/comments/all',
        description='Read all the comments, included deleted comments, of a specific Task',
        responses={
            200:{'detail':'All comments, included deleted comments, obtained','model':schemas.ReadComment},
            404:{'detail':'Comments in Task not found','model':responses.NotFound},
            500:{'detail':'Internal error', 'model':responses.DatabaseErrorResponse}
        })
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
            logger.error(f'Comments not found in Task {task_id}')
            raise exceptions.CommentNotFoundError(task_id)

        return comments_found

    except SQLAlchemyError as e:
        logger.error('Internal error: {e}')
        raise exceptions.DatabaseError(e, func='get_comments')

@router.post(
        '/comments',
        description='Create a new comment on a specific task. Need "content" data string',
        response_model=responses.CommentCreateSucces,
        responses={
            201:{'detail':'Comment successfully created', 'model':schemas.CreateComment},
            404:{'detail':'Comments in Task not found', 'model':responses.NotFound},
            500:{'detail':'Internal error', 'model':responses.DatabaseErrorResponse}
        })
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

        return {'detail':'New comment created'}

    except SQLAlchemyError as e:
        logger.error('Error interno: {e}')
        raise exceptions.DatabaseError(e, func='create_comment')

@router.patch(
        '/comments/{comment_id}',
        description='Update a comment on a specific Task. You can change "content" string, "is_deleted" bool if you want to hide the commentary, and the update date will be saved',
        responses={
                200:{'detail':'Comment successfully updated', 'model':schemas.UpdateComment},
                401:{'detail':'User not authorized to comment in this Task', 'model':responses.NotAuthorized},
                404:{'detail':'Comments in Task not found', 'model':responses.NotFound},
                500:{'detail':'Internal error', 'model':responses.DatabaseErrorResponse}
            })
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

        return {'detail':'Comment successfully updated'}

    except SQLAlchemyError as e:
        logger.error('Error interno: {e}')
        raise exceptions.DatabaseError(e, func='update_comment')

@router.delete(
        '/comments/{comment_id}',
        description='Delete the comment on a specific task. It will not be completely eliminated, but will be available to those who have permissions. ',
        responses={
                200:{'detail':'Comment successfully deleted'},
                401:{'detail':'User not authorized to comment in this Task'},
                404:{'detail':'Comments in Task not found'},
                500:{'detail':'Internal error'}
            })
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
            logger.error(f'Comment not found in Task {task_id}')
            raise exceptions.CommentNotFoundError(task_id)

        if comment_found.user_id != user.user_id:
            logger.error(f'User {user.user_id} not authorized')
            raise exceptions.UserNotAuthorizedInCommentError(user.user_id, comment_id)

        # Actualizando el estado
        comment_found.is_deleted = True

        session.commit()

        return {'detail':'Comment successfully deleted'}

    except SQLAlchemyError as e:
        logger.error('Internal error: {e}')
        raise exceptions.DatabaseError(e, func='update_comment')