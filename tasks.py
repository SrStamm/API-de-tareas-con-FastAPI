from celery import Celery
from typing import List
import os
from dotenv import load_dotenv
from db.database import SessionLocal, sessionlocal, select, SQLAlchemyError
from models import db_models, schemas
from core.logger import logger

load_dotenv()

host= os.getenv("REDIS_HOST", "localhost")
port=int(os.getenv("REDIS_PORT", '6379'))
db=int(os.getenv("REDIS_DB", '0'))
password=os.getenv("REDIS_PASSWORD")

url = f"redis://{host}:{port}/{db}"

app = Celery('tasks', broker=url)

@app.task
def get_pending_notifications_for_user(user_id: int) -> List[db_models.Notifications]:
    session = sessionlocal
    try:
        stmt = select(db_models.Notifications).where(
            db_models.Notifications.user_id == user_id,
            db_models.Notifications.status == db_models.Notify_State.SIN_ENVIAR)

        notify_found = session.exec(stmt).all()

        return notify_found

    except SQLAlchemyError as e:
        logger.error(f'[get_pending_notifications_for_user] Internal Error | Error: {str(e)}.')
        raise

    except Exception as e:
        logger.error(f'[get_pending_notifications_for_user] Notification Error | Error: {str(e)}.')
        return []

@app.task
def save_notification_in_db(message, user_id: int):
    session = SessionLocal()
    try:
        notice_payload = schemas.NotificationPayload(**message)

        new_notice = db_models.Notifications(
            user_id=user_id,
            type=notice_payload.notification_type,
            payload=notice_payload.message,
            status=db_models.Notify_State.SIN_ENVIAR
        )

        session.add(new_notice)
        session.commit()
        logger.info(f'[save_notification] Saved notification for user {user_id}, type: {notice_payload.notification_type}')
        return {"status": "success", "notification_id": new_notice.id}

    except ValueError as ve:
        logger.error(f'[save_notification_in_db] Validation error for user {user_id}: {str(ve)}')
        session.rollback()
        raise

    except SQLAlchemyError as dbe:
        logger.error(f'[save_notification_in_db] Database error for user {user_id}: {str(dbe)}')
        session.rollback()
        raise

    except Exception as e:
        logger.error(f'[save_notification_in_db] Unexpected error for user {user_id}: {str(e)}')
        session.rollback()
        raise

    finally:
        session.close()