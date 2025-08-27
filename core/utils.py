from db.database import Session, select
from models.exceptions import UserNotInProjectError
from models.db_models import project_user
from .logger import logger


def found_user_in_project_or_404(user_id: int, project_id: int, session: Session):
    stmt = select(project_user).where(
        project_user.user_id == user_id,
        project_user.project_id == project_id,
    )

    user = session.exec(stmt).first()

    if not user:
        logger.error(f"User {user_id} no encontrado en project {project_id}")
        raise UserNotInProjectError(user_id=user_id, project_id=project_id)
    user = session.get
    return user
