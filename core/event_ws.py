from models import schemas

def format_notification(notification_type:str, message:str):
    # Crea la notificacion
    outgoin_payload = schemas.OutgoingNotificationPayload(
        notification_type=notification_type,
        message=message
    ).model_dump()

    # Crea el evento
    outgoing_event = schemas.WebSocketEvent(
        type='notification',
        payload=outgoin_payload
    )

    # Parsea a json
    outgoin_event_json = outgoing_event.model_dump_json()
    
    return outgoin_event_json