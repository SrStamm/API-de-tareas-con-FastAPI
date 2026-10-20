from celery import Celery
from typing import List
import os
import json
from dotenv import load_dotenv
from db.database import SessionLocal, select, SQLAlchemyError
from models import db_models, schemas
from core.logger import logger

load_dotenv()

host = os.getenv("REDIS_HOST", "localhost")
port = int(os.getenv("REDIS_PORT", "6379"))
db = int(os.getenv("REDIS_DB", "0"))
password = os.getenv("REDIS_PASSWORD")

url = f"redis://{host}:{port}/{db}"

app = Celery("tasks", broker=url)


def get_pending_notifications_for_user_sync(user_id: int) -> List[db_models.Notifications]:
    session = SessionLocal()
    try:
        stmt = select(db_models.Notifications).where(
            db_models.Notifications.user_id == user_id,
            db_models.Notifications.status == db_models.Notify_State.SIN_ENVIAR,
        )

        notify_found = session.exec(stmt).all()
        session.close()
        return notify_found

    except SQLAlchemyError as e:
        session.close()
        logger.error(
            f"[get_pending_notifications_for_user] Internal Error | Error: {str(e)}."
        )
        raise

    except Exception as e:
        session.close()
        logger.error(
            f"[get_pending_notifications_for_user] Notification Error | Error: {str(e)}."
        )
        return []


@app.task(retry_backoff=5)
def get_pending_notifications_for_user(user_id: int) -> List[db_models.Notifications]:
    return get_pending_notifications_for_user_sync(user_id)


@app.task
def deliver_pending_notifications(user_id: int):
    from core.event_ws import format_notification
    from core.socket_manager import manager
    import asyncio

    session = SessionLocal()
    try:
        pending = get_pending_notifications_for_user_sync(user_id)
        if not pending:
            session.close()
            return {"detail": "No habian notificaciones a enviar"}
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    async def _deliver():
        nonlocal pending, session
        for n in pending:
            notification_to_send = format_notification(
                notification_type=n.type, message=n.payload
            )
            await manager.send_to_user(user_id=user_id, message=notification_to_send)
            n.status = db_models.Notify_State.ENVIADO
        session.commit()
        session.close()
        logger.info(f"[deliver_pending_notifications] Notifications were updated")

    return loop.run_until_complete(_deliver())


@app.task
def save_notification_in_db(message, user_id: int):
    session = SessionLocal()
    try:
        message_decoded = json.loads(message)["payload"]
        notice_payload = schemas.NotificationPayload(**message_decoded)

        new_notice = db_models.Notifications(
            user_id=user_id,
            type=notice_payload.notification_type,
            payload=notice_payload.message,
            status=db_models.Notify_State.SIN_ENVIAR,
        )

        session.add(new_notice)
        session.commit()
        logger.info(
            f"[save_notification] Saved notification for user {user_id}, type: {notice_payload.notification_type}"
        )
        return {"status": "success", "notification_id": new_notice.id}

    except ValueError as ve:
        logger.error(
            f"[save_notification_in_db] Validation error for user {user_id}: {str(ve)}"
        )
        session.rollback()
        raise

    except SQLAlchemyError as dbe:
        logger.error(
            f"[save_notification_in_db] Database error for user {user_id}: {str(dbe)}"
        )
        session.rollback()
        raise

    except Exception as e:
        logger.error(
            f"[save_notification_in_db] Unexpected error for user {user_id}: {str(e)}"
        )
        session.rollback()
        raise

    finally:
        session.close()

