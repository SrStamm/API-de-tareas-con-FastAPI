from core.logger import logger
from db.database import Session, select, SQLAlchemyError, or_
from models.db_models import User, Session as SessionDB
from datetime import datetime, timezone

from models.exceptions import DatabaseError


class AuthRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_user_by_id(self, user_id: int):
        stmt = select(User).where(User.user_id == user_id)
        return self.session.exec(stmt).first()

    def get_user_whit_username(self, username: str):
        stmt = select(User).where(User.username == username)
        return self.session.exec(stmt).first()

    def new_session(self, jti: str, sub: str, expires_at: datetime):
        try:
            new_session = SessionDB(jti=jti, sub=sub, expires_at=expires_at)
            self.session.add(new_session)
            self.session.commit()
            self.session.refresh(new_session)
            return new_session
        except SQLAlchemyError as e:
            logger.error(f"[AuthRepository.new_session] Database error: {e}")
            raise DatabaseError(e, "[AuthRepository.new_session]")

    def delete_session(self, actual_session: SessionDB):
        self.session.delete(actual_session)
        self.session.commit()

    def get_session_with_jti(self, jti: str):
        stmt = select(SessionDB).where(SessionDB.jti == jti)
        return self.session.exec(stmt).first()

    def get_active_sessions(self, user_id):
        stmt = select(SessionDB).where(
            SessionDB.sub == user_id, SessionDB.is_active == True
        )
        return self.session.exec(stmt).all()

    def get_expired_sessions(self):
        stmt = select(
            SessionDB.sub,
            SessionDB.is_active,
            SessionDB.expires_at,
        ).where(
            or_(
                SessionDB.is_active == False,
                SessionDB.expires_at < datetime.now(timezone.utc),
            )
        )
        return self.session.exec(stmt).all()
