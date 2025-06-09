from repositories.project_repositories import ProjectRepository
from services.group_service import GroupService
from services.user_services import UserService
from models import exceptions
from models.db_models import User
from models.schemas import ReadBasicProject, CreateProject, UpdateProject, ReadProjectUser, UpdatePermissionUser
from db.database import redis_client, redis
from core.logger import logger
from core.socket_manager import manager
from core.event_ws import format_notification
import json
from typing import List

class ProjectService:
    def __init__(self, project_repo: ProjectRepository, group_serv: GroupService, user_serv: UserService):
        self.project_repo = project_repo
        self.group_serv = group_serv
        self.user_serv = user_serv

    def found_project_or_404(self, group_id:int, project_id:int):
        founded_project = self.project_repo.get_project_by_id(group_id, project_id)

        if not founded_project:
            logger.error(f'Project {project_id} no encontrado')
            raise exceptions.ProjectNotFoundError(project_id)

        return founded_project

    def found_user_in_project_or_404(self, user_id:int, project_id:int) -> User:
        user = self.project_repo.get_user_in_project(user_id, project_id)
        
        if not user:
            logger.error(f'User {user_id} no encontrado en project {project_id}')
            raise exceptions.UserNotInProjectError(user_id=user_id, project_id=project_id)
        
        return user

    async def get_projects_iam(self, user_id: int, limit: int, skip: int) -> List[ReadBasicProject]:
        key = f'project:user:user_id:{user_id}:limit:{limit}:offset:{skip}'
        cached = await redis_client.get(key)

        # Devuelve si es verdad
        if cached:
            logger.info(f'[get_projects_iam] Redis Cache HIT - Key: {key}')
            return json.loads(cached)

        found_projects = self.project_repo.get_all_project_by_user(user_id, limit, skip)

        # Cachea la respuesta
        to_cache = [
            ReadBasicProject(group_id=group_id, project_id=project_id, title=title)
            for group_id, project_id, title in found_projects
            ]

        # Guarda la respuesta
        try:
            await redis_client.setex(key, 6000, json.dumps([project_.model_dump() for project_ in to_cache], default=str))
            logger.info(f'[get_projects_iam] Redis Cache Success - Key {key}')
        except redis.RedisError as e:
            logger.warning(f'[get_projects_iam] Redis Cache Error | Error: {e}')

        return to_cache

    async def get_all_projects(self, group_id: int, limit: int, skip: int):
        key = f'projects:group_id:{group_id}:limit:{limit}:offset:{skip}'
        cached = await redis_client.get(key)

        # Devuelve si es verdad
        if cached:
            logger.info(f'[get_projects] Redis Cache Hit - Key: {key}')
            return json.loads(cached)

        self.group_serv.get_group_or_404(group_id)

        found_projects = self.project_repo.get_all_projects(group_id, limit, skip)

        to_cache = [
            {
                **project.model_dump(),
                'users': [user.model_dump() for user in project.users]
            }
            for project in found_projects]

        try:
            await redis_client.setex(key, 6000, json.dumps(to_cache, default=str))
        except redis.RedisError as e:
            logger.error(f'[get_projects] Redis Cache Error | Error: {str(e)}')

        return to_cache

    async def get_user_in_project(self, group_id: int, project_id: int, limit:int, skip: int):
        key = f'project:users:group_id:{group_id}:project_id:{project_id}:limit:{limit}:offset:{skip}'
        cached = await redis_client.get(key)

        if cached:
            logger.info(f'[get_user_in_project] Redis Cache Hit - Key: {key}')
            return json.loads(cached)

        project = self.found_project_or_404(group_id, project_id)

        results = self.project_repo.get_users_in_project(project_id, limit, skip)

        if not results:
            logger.error(f'[get_user_in_project] Users in Project {project_id} Error | Users not found in Project')
            raise exceptions.UsersNotFoundInProjectError(project_id=project_id)

        # El resultado son tuplas, entonces se debe hacer lo siguiente para que devuelva la informacion solicitada
        to_cache = [
            ReadProjectUser(user_id=user_id, username=username, permission=permission)
            for user_id, username, permission in results
        ]

        try:
            await redis_client.setex(key, 600, json.dumps([project.model_dump() for project in to_cache], default=str))
            logger.info(f'[get_user_in_project] Redis Cache Set - Key: {key}')
        except redis.RedisError as e:
            logger.warning(f'[get_user_in_project] Redis Cache Set Error | Error: {str(e)}')

        return to_cache

    async def create_project(self, group_id: int, user_id: int, project: CreateProject):
        self.group_serv.get_group_or_404(group_id)

        self.project_repo.create(
            group_id,
            user_id,
            project
        )

        try:
            await redis_client.delete('projects:group_id:{group_id}:limit:*:offset:*')
        except redis.RedisError as e:
            logger.warning(f'Error al cachear en Redis {e}')

        return {'detail':'Se ha creado un nuevo proyecto de forma exitosa'}

    async def update_project(self, group_id: int, project_id: int, update_project: UpdateProject):
        try:
            found_project = self.found_project_or_404(group_id, project_id)

            self.project_repo.update(found_project, update_project)

            try:
                await redis_client.delete('projects:group_id:{group_id}:limit:*:offset:*')
                logger.info(f'[update_project] Redis Cache Delete - Key: projects:group_id:{group_id}:limit:*:offset:*')
            except redis.RedisError as e:
                logger.error(f'[update_project] Redis Cache Delete Error | Error: {str(e)}')

            return {'detail':'Se ha actualizado la informacion del projecto'}
        except Exception:
            raise

    async def delete_project(self, group_id: int, project_id: int):
        try:
            found_project = self.found_project_or_404(group_id, project_id)

            self.project_repo.delete(found_project)

            try:
                await redis_client.delete('projects:group_id:{group_id}:limit:*:offset:*')
                await redis_client.delete('project:users:group_id:{group_id}:project_id:{project_id}:limit:*:offset:*')
                
                logger.info(f'[delete_project] Redis Cache Delete Succes - Key: projects:group_id:{group_id}:limit:*:offset:*')
                logger.info(f'[delete_project] Redis Cache Delete Succes - Key: project:users:group_id:{group_id}:project_id:{project_id}:limit:*:offset:*')
            except redis.RedisError as e:
                logger.warning(f'[delete_project] Redis Cache Delete Error | Error: {str(e)}')

            return {'detail':'Se ha eliminado el proyecto'}
        except Exception:
            raise

    async def add_user(self, group_id: int, project_id: int, user_id: int):
        try:
            project = self.found_project_or_404(group_id, project_id)

            user = self.user_serv.get_user_or_404(user_id)

            group = await self.group_serv.get_group_or_404(group_id)

            if not user in group.users:
                logger.error(f'[add_user_to_project] Add user to Project Error | Error User {user_id} not exist in Group {group_id}')
                raise exceptions.UserNotInGroupError(user_id=user_id, group_id=group_id)

            if user in project.users:
                logger.error(f'[add_user_to_project] Add user to Project Error | Error User {user_id} exists in Proyect {project_id}')
                raise exceptions.UserInProjectError(user_id=user_id, project_id=project_id)

            self.project_repo.add_user(project_id, user_id)

            outgoing_event_json = format_notification(
                notification_type='add_user_to_project',
                message=f'You were added to the project {project_id}')

            # Envia el evento
            await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

            # Elimina cache
            try:
                await redis_client.delete('project:users:group_id:{group_id}:project_id:{project_id}:limit:*:offset:*')
                await redis_client.delete('projects:group_id:{group_id}:limit:*:offset:*')
            
                logger.info(f'[add_user_to_project] Redis Cache Delete Success - Key: project:users:group_id:{group_id}:project_id:{project_id}:limit:*:offset:*')
                logger.info(f'[add_user_to_project] Redis Cache Delete Success - Key: projects:group_id:{group_id}:limit:*:offset:*')
            except redis.RedisError as e:
                logger.warning(f'[add_user_to_project] Redis Cache Delete Error | Error: {str(e)}')

            return {'detail':'El usuario ha sido agregado al proyecto'}
        except Exception:
            raise

    async def remove_user(self, group_id: int, project_id: int, user_id: int):
        try:
            project = self.found_project_or_404(group_id, project_id)

            user = self.user_serv.get_user_or_404(user_id)

            group = await self.group_serv.get_group_or_404(group_id)

            if not user in group.users:
                logger.error(f'[remove_user_from_project] Remove User to Project Error | User {user_id} not exist in Group {group_id}')
                raise exceptions.UserNotInGroupError(user_id=user_id, group_id=group_id)

            if user in project.users:
                user_ = self.project_repo.get_user_in_project(project_id, user_id)
                self.project_repo.remove_user(user_)

                outgoing_event_json = format_notification(
                notification_type='delete_user_from_project',
                message=f'You were deleted from the project {project_id}'
                )

                # Envia el evento
                await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

                # Elimina cache
                try:
                    await redis_client.delete('project:users:group_id:{group_id}:project_id:{project_id}:limit:*:offset:*')
                    await redis_client.delete('projects:group_id:{group_id}:limit:*:offset:*')

                    logger.info(f'[remove_user_from_project] Redis Cache Delete Success - Key: project:users:group_id:{group_id}:project_id:{project_id}:limit:*:offset:*')
                    logger.info(f'[remove_user_from_project] Redis Cache Delete Success - Key: projects:group_id:{group_id}:limit:*:offset:*')
                except redis.RedisError as e:
                    logger.warning(f'[remove_user_from_project] Redis Cache Delete Error | Error: {str(e)}')

                return {'detail':'El usuario ha sido eliminado del proyecto'}
            else:
                logger.error(f'[remove_user_from_project] Delete User to Project Error | User {user_id} not exists in Project {project_id}')
                raise exceptions.UserNotInProjectError(user_id=user_id, project_id=project_id)
        except Exception:
            raise

    async def update_user_permission_in_project(self, group_id: int, project_id: int, user_id: int, permission: UpdatePermissionUser):
        try:
            self.found_project_or_404(group_id, project_id)

            user = self.project_repo.get_user_in_project(project_id, user_id)

            if not user:
                logger.error(f'[update_user_permission_in_project] User {user_id} not exists in proyect {project_id}')
                raise exceptions.UserNotInProjectError(project_id=project_id, user_id=user_id)

            user = self.project_repo.update_permission(user, permission)

            outgoing_event_json = format_notification(
                notification_type='permission_update',
                message=f'Permissions of the project {project_id} were updated to {user.permission.value}'
                )

            await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

            try:
                await redis_client.delete('project:users:group_id:{group_id}:project_id:{project_id}:limit:*:offset:*')
                logger.info(f'[update_user_permission_in_project] Redis Cache Delete Success - Key: project:users:group_id:{group_id}:project_id:{project_id}:limit:*:offset:*')
            except redis.RedisError as e:
                logger.warning(f'[update_user_permission_in_project] Redis Cache Delete Error | Error {str(e)}')

            return {'detail':'Se ha cambiado los permisos del usuario en el proyecto'}

        except Exception:
            raise