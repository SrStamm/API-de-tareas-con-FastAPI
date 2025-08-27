from repositories.comment_repositories import CommentRepository
from dependency.task_dependencies import TaskService, get_task_service
from db.database import get_session, Session
from fastapi import Depends

from services.comment_services import CommentService


def get_comment_repository(session: Session = Depends(get_session)):
    return CommentRepository(session)


def get_comment_service(
    comment_repo: CommentRepository = Depends(get_comment_repository),
    task_ser: TaskService = Depends(get_task_service),
) -> CommentService:
    return CommentService(comment_repo, task_ser)
