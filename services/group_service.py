from repositories.group_repositories import GroupRepository
from models.schemas import ReadGroup, CreateGroup, ReadGroupUser, UpdateGroup
from models.db_models import Group_Role
from models import exceptions
from typing import List
from db.database import redis_client, redis
from core.logger import logger
from repositories.user_repositories import UserRepository
from core.socket_manager import manager
from core.event_ws import format_notification
import json

class GroupService:
    def __init__(self, group_repo: GroupRepository, user_repo: UserRepository):
        self.group_repo = group_repo
        self.user_repo = user_repo

    async def get_group_or_404(self, group_id: int):
        group = self.group_repo.get_group_by_id(group_id)

        if not group:
            logger.error(f'Group {group_id} no encontrado')
            raise exceptions.GroupNotFoundError(group_id)

        return group

    def role_of_user_in_group(self, user_id: int, group_id: int):
        found_user = self.group_repo.get_role_for_user_in_group(group_id, user_id)

        if not found_user:
            raise exceptions.UserNotInGroupError(user_id=user_id, group_id=group_id)

        return found_user.role

    async def get_groups_with_cache(self, limit:int, skip:int) -> List[ReadGroup]:
        # Cache logic
        key = f'groups:limit:{limit}:offset:{skip}'
        cached = await redis_client.get(key)

        if cached:
            logger.info(f'[get_groups_with_cache] Cache HIT - Key: {key}')
            return json.loads(cached)

        # Get from repository
        found_groups = self.group_repo.get_all_groups(limit, skip)

        # Transform to response format
        to_cache = [
            {
                **group.model_dump(),
                'users': [user.model_dump() for user in group.users]
            }
            for group in found_groups
        ]

        # Cache the response
        try:
            await redis_client.setex(key, 300, json.dumps(to_cache, default=str))
            logger.info(f'[get_groups] Cache SET - Key: {key}')
        except redis.RedisError as e:
            logger.warning(f'[get_groups] Cache FAIL - Key: {key} | Error: {e}') 

        return to_cache

    async def get_groups_where_user_in(self, user_id: int, limit: int, skip: int):
        # Cache logic
        key = f'groups:user_id:{user_id}:limit:{limit}:offset:{skip}'
        cached = await redis_client.get(key)
        if cached:
            logger.info(f'[get_groups_wher_user_in] Cache Hit - Key: {str(key)}')
            return json.loads(cached)

        # Get from repository
        found_groups = self.group_repo.get_groups_for_user(user_id, limit, skip)

        # Transform to response format
        to_cache = [
            {
                **group.model_dump(),
                'users': [user.model_dump() for user in group.users]
            }
            for group in found_groups]

        # Cache the response
        try:
            await redis_client.setex(key, 600, json.dumps(to_cache, default=str))
            logger.info(f'[get_groups_in_user] Cache Set - Key: {str(key)}')
        except redis.RedisError as e:
            logger.warning(f'[get_groups_in_user] Cache Fail | Error: {str(e)}')

        return to_cache

    async def get_users_in_group(self, group_id: int, limit: int, skip: int):
        key = f'groups:users:group_id:{group_id}:limit:{limit}:offset:{skip}'
        cached = await redis_client.get(key)

        if cached:
            logger.info(f'[get_user_in_group] Cache Hit - Key: {key}')
            return json.loads(cached)

        # Se debe hacer cambios en utils que utilicen los repositorios
        await self.get_group_or_404(group_id)

        users_found = self.group_repo.get_users_for_group(group_id)

        # Transform to response format
        to_cache = [
            ReadGroupUser(user_id=user_id, username=username, role=role.value)
            for username, user_id, role in users_found
        ]

        # Cache the response
        try:
            await redis_client.setex(key, 600, json.dumps([user_.model_dump() for user_ in to_cache], default=str))
            logger.info(f'[get_groups] Cache Set - Key: {key}')
        except redis.RedisError as e:
            logger.warning(f'[get_groups] Cache Fail | Error: {str(e)}')

        return to_cache

    async def create_group(self, new_group: CreateGroup, user_id: int):
        # Create a new group
        self.group_repo.create(new_group, user_id)
    
        # Delete cache
        try:
            await redis_client.delete(f'groups:limit:*:offset:*')
            logger.info(f'[create_group] Cache Delete - Key: groups:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'[create_group] Cache Delete Error | Error: {str(e)}')

        logger.info(f'[create_group] Group Create Success')
        return {'detail': 'Se ha creado un nuevo grupo de forma exitosa'}
    
    async def update_group(self, group_id, update_group: UpdateGroup, actual_user_role: Group_Role, user_id: int):
        actual_group = await self.get_group_or_404(group_id)

        if actual_user_role not in ('admin', 'editor'):
            
            raise exceptions.NotAuthorized(user_id)

        self.group_repo.update(actual_group, update_group)

        try:
            await redis_client.delete(f'groups:limit:*:offset:*')
            logger.info(f'[update_group] Cache Delete - Key: groups:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'[update_group] Cache Delete Error | Error: {str(e)}')

        logger.info(f'[update_group] Group Create Success')
        return {'detail':'Se ha actualizado la informacion del grupo'}
    
    async def delete_group(self, group_id: int):
        group = await self.get_group_or_404(group_id)

        self.group_repo.delete(group)

        try:
            await redis_client.delete(f'groups:limit:*:offset:*')
            logger.info(f'[delete_group] Cache Delete - Key: groups:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'[delete_group] Cache Delete Error | Error: {str(e)}')

        return {'detail':'Se ha eliminado el grupo'}

    async def append_user(self, group_id, user_id: int, actual_user_id: int):
        group = await self.get_group_or_404(group_id)

        user = self.user_repo.get_user_by_id(user_id)

        if not user:
            logger.error(f'User {user_id} no encontrado')
            raise exceptions.UserNotFoundError(user_id)

        if user in group.users:
            logger.error(f'[append_user_group] User {user_id} is in Group {group_id} | Error')
            raise exceptions.UserInGroupError(user_id=user.user_id, group_id=group.group_id)

        self.group_repo.append_user(group_id, user)

        # Se crea la notificacion
        outgoing_event_json = format_notification(
                notification_type='append_to_group',
                message='You were added to group {group_id}'
            )

        # Envia el evento
        await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

        try:
            await redis_client.delete(f'groups:user_id:{actual_user_id}:limit:*:offset:*')
            logger.info(f'[append_user_group] Cache Delete - Key: groups:user_id:{actual_user_id}:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'[append_user_group] Cache Delete Error | Error: {str(e)}')

        logger.info(f'[append_user_group] User {user_id} Append to Group {group_id} Success')
        return {'detail':'El usuario ha sido agregado al grupo'}

    async def delete_user(self, group_id: int, user_id: int, actual_user_id: int, actual_user_role: Group_Role):
        group = await self.get_group_or_404(group_id)

        user = self.user_repo.get_user_by_id(user_id)

        if not user:
            logger.error(f'User {user_id} no encontrado')
            raise exceptions.UserNotFoundError(user_id)

        if user in group.users:
            role_user = self.role_of_user_in_group(user_id, group_id)

            print(f'DEBBUG: rol de usuario a eliminar: {role_user}')
            print(f'DEBBUG: rol de usuario actual: {actual_user_role}')

            if role_user in ['editor', 'member'] and actual_user_role == 'admin' or role_user == 'member' and actual_user_role == 'editor':            
                self.group_repo.delete_user(group_id, user)

                # Se crea la notificacion
                outgoing_event_json = format_notification(
                        notification_type='remove_user_to_group',
                        message='You were removed to group {group_id}'
                    )

                # Envia el evento
                await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

                try:
                    await redis_client.delete(f'groups:user_id:{actual_user_id}:limit:*:offset:*')
                    logger.info(f'[delete_user] Cache Delete - Key: groups:user_id:{actual_user_id}:limit:*:offset:*')
                except redis.RedisError as e:
                    logger.warning(f'[delete_user] Cache Delete Error | Error: {str(e)}')

                logger.info(f'[delete_user] User {user_id} Delete to Group {group_id} Success')
                return {'detail':'El usuario ha sido eliminado al grupo'}
            else:
                logger.info(f'[delete_user_group] Unauthorized Error | User {actual_user_id} not authorized in group {group_id}')
                raise exceptions.NotAuthorized(actual_user_id)
        else:
            logger.error(f'[delete_user_group] User {user_id} not found in Group {group_id}')
            raise exceptions.UserNotFoundError(user_id)

    async def update_user_role(self, group_id: int, user_id: int, role: Group_Role, actual_user_id: int):
        self.get_group_or_404(group_id)

        user = self.role_of_user_in_group(user_id, group_id)

        if not user:
            logger.error(f'[update_user_role] User not found Error | User {user_id} not found in group {group_id}')
            raise exceptions.UserNotInGroupError(user_id=user_id, group_id=group_id)

        self.group_repo.update_role(user_id, role)
        
        outgoing_event_json = format_notification(
                notification_type='update_role_to_group',
                message=f'Your role in the group {group_id} was upgrated to: {role}')

        await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

        # Elimina cache existente
        try:
            await redis_client.delete(f'groups:user_id:{actual_user_id}:limit:*:offset:*')
            logger.info(f'[get_groups] Cache Delete - Key: groups:user_id:{actual_user_id}:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'[get_groups] Cache Delete Error | Error: {str(e)}')

        return {'detail':'Se ha cambiado los permisos del usuario en el grupo'}