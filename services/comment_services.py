from models.schemas import CreateComment, UpdateComment
from models.exceptions import (
    CommentNotFoundError,
    DatabaseError,
    UserNotAuthorizedInCommentError,
)
from repositories.comment_repositories import CommentRepository
from services.task_services import TaskService
from core.event_ws import format_notification
from core.socket_manager import manager
from core.logger import logger


class CommentService:
    def __init__(
        self,
        comment_repo: CommentRepository,
        task_serv: TaskService,
    ):
        self.comment_repo = comment_repo
        self.task_serv = task_serv

    def get_comments(self, task_id: int):
        return self.comment_repo.get_comments(task_id)

    def get_all_comments(self, task_id: int):
        comments = self.comment_repo.get_all_comments(task_id)

        if not comments:
            logger.error(
                f"[get_all_comments] Not found Error | Comments not found in Task {task_id}"
            )
            raise CommentNotFoundError(task_id)

        return comments

    async def create(self, comment: CreateComment, task_id: int, user_id: int):
        try:
            new_comment = self.comment_repo.create(comment, task_id, user_id)

            users = self.comment_repo.extract_valid_mentions(comment.content)

            if users:
                users_validated = self.task_serv.validate_in_task(users, task_id)
                if users_validated:
                    payload = format_notification(
                        notification_type="comment_mention", message=f"User {user_id}"
                    )
                    await manager.send_to_user(message=payload, user_id=user_id)

            return new_comment
        except DatabaseError as e:
            logger.error(f"[CommentService.create] Repo failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"[CommentService.create] Unknown Error: {str(e)}")
            raise

    def update(
        self, update_comment: UpdateComment, comment_id: int, task_id: int, user_id: int
    ):
        try:
            comment_found = self.comment_repo.get_comment_by_id(comment_id)

            if not comment_found:
                logger.error(
                    f"[update_comment] Not Found Error | Comment not found in Task {task_id}"
                )
                raise CommentNotFoundError(task_id)

            if comment_found.user_id != user_id:
                logger.error(
                    f"[update_comment] Unauthorized Error | User {user_id} not authorized"
                )
                raise UserNotAuthorizedInCommentError(user_id, comment_id)

            comment = self.comment_repo.update(update_comment, comment_found)
            return comment
        except DatabaseError as e:
            logger.error(f"[CommentService.update] Repo failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"[CommentService.update] Unknown Error: {str(e)}")
            raise

    def delete(self, task_id: int, comment_id: int, user_id: int):
        try:
            comment_found = self.comment_repo.get_comment_by_id(comment_id)
            if not comment_found:
                logger.error(
                    f"[delete_comment] Not Found Error | Comment not found in Task {task_id}"
                )
                raise CommentNotFoundError(task_id)

            if comment_found.user_id != user_id:
                logger.error(
                    f"[delete_comment] Unauthorized Error| User {user_id} not authorized"
                )
                raise UserNotAuthorizedInCommentError(user_id, comment_id)

            self.comment_repo.delete(comment_found)

            return {"detail": "Comment successfully deleted"}
        except DatabaseError as e:
            logger.error(f"[CommentService.delete] Repo failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"[CommentService.delete] Unknown Error: {str(e)}")
            raise
