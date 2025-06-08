from models.schemas import ReadUser
from models.db_models import User
from db.database import Session, select, selectinload

class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_user_by_id(self, user_id:int) -> User:
        stmt = select(User).where(User.user_id == user_id)
        return self.session.exec(stmt).first()