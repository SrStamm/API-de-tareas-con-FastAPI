from repositories.group_repositories import GroupRepository
from repositories.user_repositories import UserRepository
from models.schemas import ReadGroup, CreateGroup, UpdateGroup
from models.db_models import Group_Role, Group
from models.exceptions import DatabaseError
from models import exceptions
from core.logger import logger

from core.socket_manager import manager
from core.event_ws import format_notification
from typing import List


class GroupService:
    def __init__(self, group_repo: GroupRepository, user_repo: UserRepository):
        self.group_repo = group_repo
        self.user_repo = user_repo

    def get_group_or_404(self, group_id: int) -> Group:
        group = self.group_repo.get_group_by_id(group_id)

        if not group:
            raise exceptions.GroupNotFoundError(group_id)

        return group

    def role_of_user_in_group(self, user_id: int, group_id: int):
        found_user = self.group_repo.get_role_for_user_in_group(group_id, user_id)

        if not found_user:
            raise exceptions.UserNotInGroupError(user_id=user_id, group_id=group_id)

        return found_user.role

    def get_user_data_for_group(self, user_id: int, group_id: int):
        try:
            found_user = self.group_repo.get_role_for_user_in_group(group_id, user_id)

            if not found_user:
                raise exceptions.UserNotInGroupError(user_id=user_id, group_id=group_id)

            return found_user
        except Exception:
            raise

    async def get_groups_with_cache(self, limit: int, skip: int) -> List[ReadGroup]:
        try:
            # Get from repository
            return self.group_repo.get_all_groups(limit, skip)

        except DatabaseError:
            raise

    async def get_groups_where_user_in(self, user_id: int, limit: int, skip: int):
        try:
            return self.group_repo.get_groups_for_user(user_id, limit, skip)

        except DatabaseError:
            raise

    async def get_users_in_group(self, group_id: int):
        try:
            # TODO: Se debe hacer cambios en utils que utilicen los repositorios
            self.get_group_or_404(group_id)

            return self.group_repo.get_users_for_group(group_id)

        except DatabaseError:
            raise

    async def create_group(self, new_group: CreateGroup, user_id: int) -> ReadGroup:
        try:
            # Create a new group
            group = self.group_repo.create(new_group, user_id)

            logger.info("group_created", user_id=user_id)

            return group

        except DatabaseError:
            raise

    async def update_group(
        self,
        group_id,
        update_group: UpdateGroup,
        actual_user_role: Group_Role,
        user_id: int,
    ) -> ReadGroup:
        try:
            actual_group = self.get_group_or_404(group_id)

            if actual_user_role not in ("admin", "editor"):
                raise exceptions.NotAuthorized(user_id)

            group_updated = self.group_repo.update(actual_group, update_group)

            logger.info("group_updated", group_id=group_id, user_id=user_id)

            return group_updated

        except DatabaseError:
            raise

    async def delete_group(self, group_id: int, user_id: int):
        try:
            group = self.get_group_or_404(group_id)

            self.group_repo.delete(group)

            logger.info("group_deleted", group_id=group_id, user_id=user_id)

            return {"detail": "Se ha eliminado el grupo"}

        except DatabaseError:
            raise

    async def append_user(self, group_id, user_id: int):
        try:
            group = self.get_group_or_404(group_id)

            user = self.user_repo.get_user_by_id(user_id)

            if not user:
                raise exceptions.UserNotFoundError(user_id)

            if user in group.users:
                raise exceptions.UserInGroupError(
                    user_id=user.user_id, group_id=group.group_id
                )

            self.group_repo.append_user(group_id, user)

            # Se crea la notificacion
            outgoing_event_json = format_notification(
                notification_type="append_to_group",
                message=f"You were added to group {group_id}",
            )

            # Envia el evento
            await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

            logger.info(
                "append_user_group",
                user_id=user_id,
                group_id=group_id,
            )

            return {"detail": "El usuario ha sido agregado al grupo"}

        except DatabaseError:
            raise

    async def delete_user(
        self,
        group_id: int,
        user_id: int,
        actual_user_id: int,
        actual_user_role: Group_Role,
    ):
        try:
            group = self.get_group_or_404(group_id)

            user = self.user_repo.get_user_by_id(user_id)

            if not user:
                raise exceptions.UserNotFoundError(user_id)

            if user in group.users:
                role_user = self.role_of_user_in_group(user_id, group_id)

                if (
                    role_user in ["editor", "member"]
                    and actual_user_role == "admin"
                    or role_user == "member"
                    and actual_user_role == "editor"
                ):
                    self.group_repo.delete_user(group_id, user)

                    # Se crea la notificacion
                    outgoing_event_json = format_notification(
                        notification_type="remove_user_to_group",
                        message=f"You were removed to group {group_id}",
                    )

                    # Envia el evento
                    await manager.send_to_user(
                        message=outgoing_event_json, user_id=user_id
                    )

                    logger.info(
                        "removed_user_from_the_group",
                        group_id=group_id,
                        user_id=user_id,
                    )

                    return {"detail": "El usuario ha sido eliminado del grupo"}
                else:
                    logger.warning(
                        "not_authorized_to_remove_user_from_the_group",
                        group_id=group_id,
                        user_id=actual_user_id,
                    )
                    raise exceptions.NotAuthorized(actual_user_id)
            else:
                raise exceptions.UserNotFoundError(user_id)

        except DatabaseError:
            raise

    async def update_user_role(
        self,
        group_id: int,
        user_id: int,
        role: Group_Role,
    ):
        try:
            self.get_group_or_404(group_id)

            user = self.role_of_user_in_group(user_id, group_id)

            if not user:
                raise exceptions.UserNotInGroupError(user_id=user_id, group_id=group_id)

            self.group_repo.update_role(user_id, role)

            logger.info(
                "update_user_role_in_group",
                group_id=group_id,
                user_id=user_id,
                role=role.value,
            )

            outgoing_event_json = format_notification(
                notification_type="update_role_to_group",
                message=f"Your role in the group {group_id} was upgrated to: {role}",
            )

            await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

            return {"detail": "Se ha cambiado los permisos del usuario en el grupo"}

        except DatabaseError:
            raise
