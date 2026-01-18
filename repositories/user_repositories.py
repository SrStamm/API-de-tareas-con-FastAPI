from models.schemas import CreateUser, UpdateUser
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
        except Exception:
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

    def update(self, user: User, update_user: UpdateUser):
        try:
            if user.username != update_user.username and update_user.username:
                user.username = update_user.username

            if user.email != update_user.email and update_user.email:
                user.email = update_user.email

            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(e, "update")
