from db.database import Session, select, selectinload
from models import db_models, exceptions
from .logger import logger
from db.database import select, Session
from typing import List
import re


def found_user_in_project_or_404(user_id: int, project_id: int, session: Session):
    stmt = select(db_models.project_user).where(
        db_models.project_user.user_id == user_id,
        db_models.project_user.project_id == project_id,
    )

    user = session.exec(stmt).first()

    if not user:
        logger.error(f"User {user_id} no encontrado en project {project_id}")
        raise exceptions.UserNotInProjectError(user_id=user_id, project_id=project_id)
    user = session.get
    return user

