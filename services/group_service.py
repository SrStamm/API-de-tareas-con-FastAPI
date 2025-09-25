from services.cache_service import cache_manager
from repositories.group_repositories import GroupRepository
from repositories.user_repositories import UserRepository
from models.schemas import ReadGroup, CreateGroup, ReadGroupUser, UpdateGroup
from models.db_models import Group_Role, Group
from models.exceptions import DatabaseError
from models import exceptions
from core.logger import logger

# from core.socket_manager import manager
from core.event_ws import format_notification
from typing import List


class GroupService:
    def __init__(self, group_repo: GroupRepository, user_repo: UserRepository):
        self.group_repo = group_repo
        self.user_repo = user_repo

    def get_group_or_404(self, group_id: int) -> Group:
        group = self.group_repo.get_group_by_id(group_id)

        if not group:
            logger.error(f"Group {group_id} no encontrado")
            raise exceptions.GroupNotFoundError(group_id)

        return group

    def role_of_user_in_group(self, user_id: int, group_id: int):
        found_user = self.group_repo.get_role_for_user_in_group(group_id, user_id)

        if not found_user:
            raise exceptions.UserNotInGroupError(user_id=user_id, group_id=group_id)

        return found_user.role

    async def get_groups_with_cache(self, limit: int, skip: int) -> List[ReadGroup]:
        try:
            key = f"groups:limit:{limit}:offset:{skip}"
            cached = await cache_manager.get(key, "get_groups_with_cache")

            if cached:
                return [ReadGroup(**group) for group in cached]

            # Get from repository
            found_groups = self.group_repo.get_all_groups(limit, skip)

            # Transform to response format
            to_cache = [
                {
                    **group.model_dump(),
                    "users": [user.model_dump() for user in group.users],
                }
                for group in found_groups
            ]

            # Cache the response
            await cache_manager.set(
                key,
                to_cache,
                "get_groups_with_cache",
            )

            return to_cache
        except DatabaseError as e:
            logger.error(f"[GroupService.get_groups_with_cache] Error: {e}")
            raise

    async def get_groups_where_user_in(self, user_id: int, limit: int, skip: int):
        try:
            # Cache logic
            key = f"groups:user_id:{user_id}:limit:{limit}:offset:{skip}"
            cached = await cache_manager.get(key, "get_groups_wher_user_in")
            if cached:
                return [ReadGroup(**group) for group in cached]

            # Get from repository
            found_groups = self.group_repo.get_groups_for_user(user_id, limit, skip)

            # Transform to response format
            to_cache = [
                {
                    **group.model_dump(),
                    "users": [user.model_dump() for user in group.users],
                }
                for group in found_groups
            ]

            # Cache the response
            await cache_manager.set(key, to_cache, "get_groups_wher_user_in")

            return to_cache
        except DatabaseError as e:
            logger.error(f"[GroupService.get_groups_where_user_in] Error: {e}")
            raise

    async def get_users_in_group(self, group_id: int, limit: int, skip: int):
        try:
            key = f"groups:users:group_id:{group_id}:limit:{limit}:offset:{skip}"
            cached = await cache_manager.get(key, "get_users_in_group")

            if cached:
                return [ReadGroupUser(**user) for user in cached]

            # Se debe hacer cambios en utils que utilicen los repositorios
            self.get_group_or_404(group_id)

            users_found = self.group_repo.get_users_for_group(group_id)

            # Transform to response format
            to_cache = [
                ReadGroupUser(user_id=user_id, username=username, role=role.value)
                for username, user_id, role in users_found
            ]

            # Cache the response
            await cache_manager.set(
                key, [user.model_dump() for user in to_cache], "get_users_in_group"
            )

            return to_cache

        except DatabaseError as e:
            logger.error(f"[GroupService.get_users_in_group] Error: {e}")
            raise

    async def create_group(self, new_group: CreateGroup, user_id: int):
        try:
            # Create a new group
            self.group_repo.create(new_group, user_id)

            # Delete cache
            await cache_manager.delete_pattern(
                "groups:limit:*:offset:*", "create_group"
            )
            # Invalida el cache del usuario que lo crea
            await cache_manager.delete_pattern(
                f"groups:user_id:{user_id}:limit:*:offset:*", "create_group"
            )

            return {"detail": "Se ha creado un nuevo grupo de forma exitosa"}
        except DatabaseError as e:
            logger.error(f"[services.create_group] Repo failed: {str(e)}")
            raise

    async def update_group(
        self,
        group_id,
        update_group: UpdateGroup,
        actual_user_role: Group_Role,
        user_id: int,
    ):
        try:
            actual_group = self.get_group_or_404(group_id)

            if actual_user_role not in ("admin", "editor"):
                raise exceptions.NotAuthorized(user_id)

            self.group_repo.update(actual_group, update_group)

            await cache_manager.delete_pattern(
                "groups:limit:*:offset:*", "update_group"
            )
            # Invalida el cache del usuario actual que lo modifica
            await cache_manager.delete_pattern(
                f"groups:user_id:{user_id}:limit:*:offset:*", "update_group"
            )

            return {"detail": "Se ha actualizado la informacion del grupo"}

        except DatabaseError as e:
            logger.error(f"[services.update_group] Repo failed: {str(e)}")
            raise

    async def delete_group(
        self, group_id: int, user_id: int
    ):  # Se agregó el parámetro user_id
        try:
            group = self.get_group_or_404(group_id)

            self.group_repo.delete(group)

            await cache_manager.delete_pattern(
                "groups:limit:*:offset:*", "delete_group"
            )
            await cache_manager.delete_pattern(
                f"groups:users:group_id:{group_id}:limit:*:offset:*", "delete_group"
            )
            # Invalida el cache del usuario actual que lo elimina
            await cache_manager.delete_pattern(
                f"groups:user_id:{user_id}:limit:*:offset:*", "delete_group"
            )

            return {"detail": "Se ha eliminado el grupo"}

        except DatabaseError as e:
            logger.error(f"[services.delete_group] Repo failed: {str(e)}")
            raise

    async def append_user(self, group_id, user_id: int, actual_user_id: int):
        try:
            group = self.get_group_or_404(group_id)

            user = self.user_repo.get_user_by_id(user_id)

            if not user:
                logger.error(f"User {user_id} no encontrado")
                raise exceptions.UserNotFoundError(user_id)

            if user in group.users:
                logger.error(
                    f"[append_user_group] User {user_id} is in Group {group_id} | Error"
                )
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
            # await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

            # Invalida el cache del usuario actual
            await cache_manager.delete_pattern(
                f"groups:user_id:{actual_user_id}:limit:*:offset:*", "append_user"
            )
            # Invalida el cache del usuario target
            await cache_manager.delete_pattern(
                f"groups:user_id:{user_id}:limit:*:offset:*", "append_user"
            )
            # Invalida el cache del grupo
            await cache_manager.delete_pattern(
                f"groups:users:group_id:{group_id}:limit:*:offset:*", "append_user"
            )

            logger.info(
                f"[append_user_group] User {user_id} Append to Group {group_id} Success"
            )
            return {"detail": "El usuario ha sido agregado al grupo"}

        except DatabaseError as e:
            logger.error(f"[services.delete_group] Repo failed: {str(e)}")
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
                logger.error(f"User {user_id} no encontrado")
                raise exceptions.UserNotFoundError(user_id)

            if user in group.users:
                role_user = self.role_of_user_in_group(user_id, group_id)

                print(f"DEBBUG: rol de usuario a eliminar: {role_user}")
                print(f"DEBBUG: rol de usuario actual: {actual_user_role}")

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
                    # await manager.send_to_user( message=outgoing_event_json, user_id=user_id)

                    # Invalida el cache del usuario actual
                    await cache_manager.delete_pattern(
                        f"groups:user_id:{actual_user_id}:limit:*:offset:*",
                        "delete_user",
                    )
                    # Invalida el cache del usuario target
                    await cache_manager.delete_pattern(
                        f"groups:user_id:{user_id}:limit:*:offset:*",
                        "delete_user",
                    )
                    # Invalida el cache del grupo
                    await cache_manager.delete_pattern(
                        f"groups:users:group_id:{group_id}:limit:*:offset:*",
                        "delete_user",
                    )

                    logger.info(
                        f"[delete_user] User {user_id} Delete to Group {group_id} Success"
                    )
                    return {"detail": "El usuario ha sido eliminado del grupo"}
                else:
                    logger.info(
                        f"[delete_user_group] Unauthorized Error | User {actual_user_id} not authorized in group {group_id}"
                    )
                    raise exceptions.NotAuthorized(actual_user_id)
            else:
                logger.error(
                    f"[delete_user_group] User {user_id} not found in Group {group_id}"
                )
                raise exceptions.UserNotFoundError(user_id)

        except DatabaseError as e:
            logger.error(f"[services.delete_user_group] Repo failed: {str(e)}")
            raise

    async def update_user_role(
        self, group_id: int, user_id: int, role: Group_Role, actual_user_id: int
    ):
        try:
            self.get_group_or_404(group_id)

            user = self.role_of_user_in_group(user_id, group_id)

            if not user:
                logger.error(
                    f"[update_user_role] User not found Error | User {user_id} not found in group {group_id}"
                )
                raise exceptions.UserNotInGroupError(user_id=user_id, group_id=group_id)

            self.group_repo.update_role(user_id, role)

            outgoing_event_json = format_notification(
                notification_type="update_role_to_group",
                message=f"Your role in the group {group_id} was upgrated to: {role}",
            )

            # await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

            # Elimina cache existente
            await cache_manager.delete_pattern(
                f"groups:user_id:{actual_user_id}:limit:*:offset:*", "update_user_role"
            )

            return {"detail": "Se ha cambiado los permisos del usuario en el grupo"}

        except DatabaseError as e:
            logger.error(f"[services.update_user_role] Repo failed: {str(e)}")
            raise
