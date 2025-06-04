from models import schemas, db_models
from logger import logger
from db.database import Session
from typing import Dict

def save_notification(message: Dict, user_id: int):
    session = Session()
    try:
        if not isinstance(message, dict):
            raise ValueError(f"Payload debe ser un dict. Recibido: {type(message)}")

        notice_payload = schemas.NotificationPayload(**message)

        new_notice = db_models.Notifications(
            user_id=user_id,
            type=notice_payload.notification_type,
            payload=notice_payload.message,
        )

        session.add(new_notice)
        session.commit()
        logger.info(f'[save_notification] Saved notification for user {user_id}.')

    except Exception as e:
        logger.error(f'[save_notification] Failed to save notification for user {user_id} | Error: {str(e)}')
        raise
    finally:
        session.close()
