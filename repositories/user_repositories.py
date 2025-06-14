from models.schemas import CreateUser
from models.db_models import User
from models.exceptions import DatabaseError
from db.database import Session, select, or_, SQLAlchemyError
from core.security import encrypt_password


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_user_by_id(self, user_id: int) -> User:
        stmt = select(User).where(User.user_id == user_id)
        return self.session.exec(stmt).first()

    def get_user_by_username_or_email(self, email, username):
        stmt = select(User).where(or_(User.email == email, User.username == username))
        return self.session.exec(stmt).first()

    def get_all_users(self, limit: int, skip: int):
        stmt = select(User.user_id, User.username).limit(limit).offset(skip)
        return self.session.exec(stmt).all()

    def create(self, user: CreateUser):
        try:
            new_user = User(**user.model_dump())
            new_user.password = encrypt_password(new_user.password)
            self.session.add(new_user)
            self.session.commit()
            return
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(e, "create")
        except Exception as e:
            self.session.rollback()
            raise

    def delete(self, user: User):
        try:
            self.session.delete(user)
            self.session.commit()
            return
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(e, "delete")
        except Exception:
            self.session.rollback()
            raise

