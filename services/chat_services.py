from typing import List

from fastapi import Depends

from dependency.project_dependencies import get_project_service
from models.schemas import ChatMessage, GroupMessagePayload, OutgoingGroupMessagePayload, WebSocketEvent
from repositories.chat_repositories import get_chat_repository, ChatRepository

from .project_services import ProjectService
from models.exceptions import ChatNotFoundError, ProjectNotFoundError, UserNotInProjectError


class ChatService:
    def __init__(self, chat_repo: ChatRepository, project_service: ProjectService):
        self.repo = chat_repo
        self.proj_serv = project_service

    def get_chat(self, project_id: int, user_id: int, limit:int , skip: int) -> List[ChatMessage]:
        try:
            self.proj_serv.found_user_in_project_or_404(user_id, project_id)

            messages = self.repo.get_chat(project_id, limit, skip)

            if not messages:
                raise ChatNotFoundError(project_id)

            return messages
        except UserNotInProjectError:
            raise ProjectNotFoundError(project_id)

    def send_message(
            self,
            project_id: int,
            user_id: int,
            payload: GroupMessagePayload,
        ):
        try:
            self.proj_serv.found_user_in_project_or_404(user_id, project_id)

            # Crea el mensaje a guardar en BD
            message = self.repo.save_message(project_id, user_id, payload.content)

            # Crea el mensaje de salida, que se envia al grupo
            outgoing_payload = OutgoingGroupMessagePayload(
                id=message.chat_id,
                project_id=project_id,
                sender_id=user_id,
                content=message.message,
                timestamp=message.timestamp,
            )

            # Crea el evento completo
            outgoing_event = WebSocketEvent(
                type="group_message", payload=outgoing_payload.model_dump()
            )

            # Parsea a json
            return outgoing_event.model_dump_json()

        except UserNotInProjectError:
            raise ProjectNotFoundError(project_id)

def get_chat_service(
    chat_repo: ChatRepository = Depends(get_chat_repository),
    project_service: ProjectService = Depends(get_project_service)
) -> ChatService:
    return ChatService(chat_repo, project_service)
