from fastapi import Depends
from sqlalchemy.orm import joinedload

from db.database import Session, get_session, select, SQLAlchemyError
from models.db_models import ProjectChat

from models.exceptions import DatabaseError


class ChatRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_chat(
        self,
        project_id: int,
        limit: int = 100,
        skip: int = 0,
    ):
        try:
            stmt = (
                select(ProjectChat)
                .options(joinedload(ProjectChat.user))
                .where(
                    ProjectChat.project_id == project_id,
                )
                .order_by(ProjectChat.timestamp.asc())
                .limit(limit)
                .offset(skip)
            )

            response = self.session.exec(stmt)
            return response.all()


        except SQLAlchemyError as e:
            raise DatabaseError(error=e, func="get_chat")

    def save_message(self, project_id: int, user_id: int, content: str):
        try:
            # Crea el mensaje a guardar en BD
            message = ProjectChat(
                project_id=project_id, user_id=user_id, message=content
            )

            self.session.add(message)
            self.session.commit()
            self.session.refresh(message)

            return message
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(error=e, func="save_message")


def get_chat_repository(session: Session = Depends(get_session)) -> ChatRepository:
    return ChatRepository(session)
