from models.schemas import (
    OutgoingNotificationPayload,
    WebSocketEvent,
    PersonalMessagePayload,
)


def format_notification(notification_type: str, message: str):
    # Crea la notificacion
    outgoin_payload = OutgoingNotificationPayload(
        notification_type=notification_type, message=message
    ).model_dump()

    # Crea el evento
    outgoing_event = WebSocketEvent(type="notification", payload=outgoin_payload)

    # Parsea a json
    outgoin_event_json = outgoing_event.model_dump_json()

    return outgoin_event_json


def format_personal_message(user_id: int, message: str):
    outgoing_payload = PersonalMessagePayload(
        content=message, received_user_id=user_id
    ).model_dump()

    outgoing_event = WebSocketEvent(
        type="personal_message", payload=outgoing_payload
    ).model_dump_json()

    return outgoing_event

