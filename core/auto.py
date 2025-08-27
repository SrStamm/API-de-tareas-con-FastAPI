from db.database import Session, select, get_session, or_, SQLAlchemyError
from models import exceptions
from models.db_models import Session as SessionDB
from datetime import datetime, timezone
from core.logger import logger


def clean_database(session: Session):
    try:
        stmt = select(SessionDB).where(
            or_(
                SessionDB.is_active == False,
                SessionDB.expires_at < datetime.now(timezone.utc),
            )
        )

        results = session.exec(stmt).all()

        if results:
            logger.info("Encontradas las sesiones")
            for result in results:
                session.delete(result)

            session.commit()
            logger.info("Sessiones eliminadas con suceso")
            logger.info(f"Se eliminaron {len(results)} sesiones expiradas")

            return

        logger.error("No hay o no se encontraron sesiones expiradas")
        return

    except SQLAlchemyError as e:
        raise exceptions.DatabaseError(e, func="get_expired_sessions")


async def run_scheduler_job():
    logger.info("Iniciando trabajo de limpieza de base de datos...")

    session_generator = get_session()
    try:
        session = next(session_generator)
        clean_database(session)

    except StopIteration:
        logger.error("get_session() no produjo una sesión.")

    finally:
        try:
            session_generator.close()

        except RuntimeError as e:
            logger.error(f"Error RuntimeError: {e}")
            pass

    logger.info("Trabajo de limpieza de base de datos finalizado.")

