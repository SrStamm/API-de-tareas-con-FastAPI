from models.db_models import Task_comments, User
from models.schemas import CreateComment, UpdateComment
from models.exceptions import DatabaseError
from db.database import Session, select, SQLAlchemyError
from typing import List
import re


class CommentRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_comment_by_id(self, comment_id: int):
        stmt = select(Task_comments).where(Task_comments.comment_id == comment_id)
        return self.session.exec(stmt).first()

    def get_comments(self, task_id: int):
        stmt = select(Task_comments, User.username).where(
            Task_comments.task_id == task_id,
            Task_comments.is_deleted == False,
            Task_comments.user_id == User.user_id,
        )

        comments = self.session.exec(stmt).all()

        comment_model = [
            {**comment_obj.model_dump(), "username": username}
            for comment_obj, username in comments
        ]

        print("comentario: ", comment_model)
        return comment_model

    def get_all_comments(self, task_id):
        stmt = select(Task_comments).where(Task_comments.task_id == task_id)
        return self.session.exec(stmt).all()

    def extract_valid_mentions(self, content: str) -> List[User]:
        mentions_raw = re.findall(r"@(\w+)", content)
        mentions = list(set(mentions_raw))

        if not mentions:
            return []

        stmt = select(User.username).where(User.username.in_(mentions))
        return self.session.exec(stmt).all()

    def create(self, new_comment: CreateComment, task_id: int, user_id: int):
        try:
            add_comment = Task_comments(
                task_id=task_id,
                user_id=user_id,
                content=new_comment.content,
            )
            self.session.add(add_comment)
            self.session.commit()
            self.session.refresh(add_comment)
            return add_comment
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(e, "create")
        except Exception:
            self.session.rollback()
            raise

    def update(self, update_comment: UpdateComment, comment: Task_comments):
        try:
            if update_comment.content:
                comment.content = update_comment.content

            comment.update_at = update_comment.update_at
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(e, "update")
        except Exception:
            self.session.rollback()
            raise

    def delete(self, comment: Task_comments):
        try:
            comment.is_deleted = True
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(e, "delete")
        except Exception:
            self.session.rollback()
            raise
