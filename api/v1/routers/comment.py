from fastapi import APIRouter, Depends, Request
from dependency.comment_dependencies import get_comment_service
from dependency.task_dependencies import get_task_service
from models import db_models, schemas, exceptions, responses
from services.comment_services import CommentService
from .auth import auth_user
from db.database import get_session, Session, select, SQLAlchemyError
from typing import List
from core.utils import (
    found_user_in_task_or_404,
    extract_valid_mentions,
    validate_in_task,
)
from core.logger import logger
from core.limiter import limiter
from core.event_ws import format_notification
from .ws import manager

router = APIRouter(prefix="/task/{task_id}", tags=["Comment"])


@router.get(
    "/comments",
    description="Read the comments of a specific Task",
    responses={
        200: {"detail": "Comments successfully obtained", "model": schemas.ReadComment},
        500: {"detail": "Internal error", "model": responses.DatabaseErrorResponse},
    },
)
@limiter.limit("100/minute")
def get_comments(
    request: Request,
    task_id: int,
    user: db_models.User = Depends(auth_user),
    comment_serv: CommentService = Depends(get_comment_service),
) -> List[schemas.ReadComment]:
    try:
        return comment_serv.get_comments(task_id, user.user_id)

    except SQLAlchemyError as e:
        logger.error(f"[get_comments] Database error | Error: {str(e)}")
        raise exceptions.DatabaseError(e, func="get_comments")


@router.get(
    "/comments/all",
    description="Read all the comments, included deleted comments, of a specific Task",
    responses={
        200: {
            "detail": "All comments, included deleted comments, obtained",
            "model": schemas.ReadComment,
        },
        404: {"detail": "Comments in Task not found", "model": responses.NotFound},
        500: {"detail": "Internal error", "model": responses.DatabaseErrorResponse},
    },
)
@limiter.limit("100/minute")
def get_all_comments(
    request: Request,
    task_id: int,
    user: db_models.User = Depends(auth_user),
    comment_serv: CommentService = Depends(get_comment_service),
) -> List[schemas.ReadComment]:
    try:
        return comment_serv.get_all_comments(task_id, user.user_id)

    except SQLAlchemyError as e:
        logger.error(f"[get_all_comments] Database Error | Error: {str(e)}")
        raise exceptions.DatabaseError(e, func="get_all_comments")


@router.post(
    "/comments",
    description='Create a new comment on a specific task. Need "content" data string',
    response_model=responses.CommentCreateSucces,
    responses={
        201: {"detail": "Comment successfully created", "model": schemas.CreateComment},
        404: {"detail": "Comments in Task not found", "model": responses.NotFound},
        500: {"detail": "Internal error", "model": responses.DatabaseErrorResponse},
    },
)
@limiter.limit("30/minute")
async def create_comment(
    request: Request,
    task_id: int,
    new_comment: schemas.CreateComment,
    user: db_models.User = Depends(auth_user),
    comment_serv: CommentService = Depends(get_comment_service),
):
    try:
        return await comment_serv.create(new_comment, task_id, user.user_id)

    except SQLAlchemyError as e:
        logger.error(f"[create_comment] Dabasae Error | Error: {str(e)}")
        raise exceptions.DatabaseError(e, func="create_comment")


@router.patch(
    "/comments/{comment_id}",
    description='Update a comment on a specific Task. You can change "content" string, "is_deleted" bool if you want to hide the commentary, and the update date will be saved',
    responses={
        200: {"detail": "Comment successfully updated", "model": schemas.UpdateComment},
        401: {
            "detail": "User not authorized to comment in this Task",
            "model": responses.NotAuthorized,
        },
        404: {"detail": "Comments in Task not found", "model": responses.NotFound},
        500: {"detail": "Internal error", "model": responses.DatabaseErrorResponse},
    },
)
@limiter.limit("30/minute")
def update_comment(
    request: Request,
    task_id: int,
    comment_id: int,
    update_comment: schemas.UpdateComment,
    user: db_models.User = Depends(auth_user),
    comment_serv: CommentService = Depends(get_comment_service),
):
    try:
        return comment_serv.update(update_comment, comment_id, task_id, user.user_id)

    except SQLAlchemyError as e:
        logger.error(f"[update_comment] Database Error | Error: {str(e)}")
        raise exceptions.DatabaseError(e, func="update_comment")


@router.delete(
    "/comments/{comment_id}",
    description="Delete the comment on a specific task. It will not be completely eliminated, but will be available to those who have permissions. ",
    responses={
        200: {"detail": "Comment successfully deleted"},
        401: {"detail": "User not authorized to comment in this Task"},
        404: {"detail": "Comments in Task not found"},
        500: {"detail": "Internal error"},
    },
)
@limiter.limit("30/minute")
def delete_comment(
    request: Request,
    task_id: int,
    comment_id: int,
    user: db_models.User = Depends(auth_user),
    comment_serv: CommentService = Depends(get_comment_service),
):
    try:
        return comment_serv.delete(task_id, comment_id, user.user_id)

    except SQLAlchemyError as e:
        logger.error(f"[delete_comment] Database Error | Error: {str(e)}")
        raise exceptions.DatabaseError(e, func="update_comment")
