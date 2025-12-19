from fastapi import APIRouter, Depends, Request
from dependency.comment_dependencies import get_comment_service
from dependency.auth_dependencies import get_current_user
from models import schemas, responses
from models.db_models import User
from services.comment_services import CommentService
from typing import List
from core.limiter import limiter

router = APIRouter(prefix="/task/{task_id}", tags=["Comment"])


@router.get(
    "/comments",
    summary="Obtain visible comments",
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
    _: User = Depends(get_current_user),
    comment_serv: CommentService = Depends(get_comment_service),
) -> List[schemas.ReadComment]:
    return comment_serv.get_comments(task_id)


@router.get(
    "/comments/all",
    summary="Get all comments",
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
    user: User = Depends(get_current_user),
    comment_serv: CommentService = Depends(get_comment_service),
) -> List[schemas.ReadComment]:
    return comment_serv.get_all_comments(task_id)


@router.post(
    "/comments",
    summary="Create a new comment",
    description='Create a new comment on a specific task. Need a "content". If mentionated a user, he receives a notification',
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
    user: User = Depends(get_current_user),
    comment_serv: CommentService = Depends(get_comment_service),
):
    return await comment_serv.create(new_comment, task_id, user.user_id)


@router.patch(
    "/comments/{comment_id}",
    summary="Update the comment",
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
    user: User = Depends(get_current_user),
    comment_serv: CommentService = Depends(get_comment_service),
):
    return comment_serv.update(update_comment, comment_id, task_id, user.user_id)


@router.delete(
    "/comments/{comment_id}",
    summary="Delete the comment",
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
    user: User = Depends(get_current_user),
    comment_serv: CommentService = Depends(get_comment_service),
):
    return comment_serv.delete(task_id, comment_id, user.user_id)
