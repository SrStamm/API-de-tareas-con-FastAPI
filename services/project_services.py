from fastapi import HTTPException
from repositories.project_repositories import ProjectRepository
from services.group_service import GroupService
from services.user_services import UserService
from models.exceptions import (
    DatabaseError,
    ProjectNotFoundError,
    UserNotInProjectError,
    UsersNotFoundInProjectError,
    UserNotInGroupError,
    UserInProjectError,
)
from models.schemas import (
    ReadBasicProject,
    CreateProject,
    UpdateProject,
    UpdatePermissionUser,
)
from core.logger import logger
from core.socket_manager import manager
from core.event_ws import format_notification
from typing import List


class ProjectService:
    def __init__(
        self,
        project_repo: ProjectRepository,
        group_serv: GroupService,
        user_serv: UserService,
    ):
        self.project_repo = project_repo
        self.group_serv = group_serv
        self.user_serv = user_serv

    def found_project_or_404(self, group_id: int, project_id: int):
        founded_project = self.project_repo.get_project_by_id(group_id, project_id)

        if not founded_project:
            logger.error(f"Project {project_id} no encontrado")
            raise ProjectNotFoundError(project_id)

        return founded_project

    def found_user_in_project_or_404(self, user_id: int, project_id: int):
        user = self.project_repo.get_user_in_project(project_id, user_id)

        if not user:
            logger.error(f"User {user_id} no encontrado en project {project_id}")
            raise UserNotInProjectError(user_id=user_id, project_id=project_id)

        return user

    def get_access_data_in_project(self, project_id: int, user_id: int):
        user = self.project_repo.get_user_permission(project_id, user_id)

        if not user:
            logger.error(f"User {user_id} no encontrado en project {project_id}")
            raise UserNotInProjectError(user_id, project_id)

        return user

    async def get_projects_iam(
        self, user_id: int, limit: int, skip: int
    ) -> List[ReadBasicProject]:
        try:
            return self.project_repo.get_all_project_by_user(user_id, limit, skip)

        except DatabaseError as e:
            logger.error(f"[project_service.get_projects_iam] Error: {e}")
            raise

    def get_projects_in_group_where_iam(self, user_id: int, group_id: int):
        try:
            return self.project_repo.get_all_project_by_user_in_group(user_id, group_id)

        except DatabaseError as e:
            logger.error(f"[project_service.get_projects_iam] Error: {e}")
            raise

    async def get_all_projects(self, group_id: int, limit: int, skip: int):
        try:
            self.group_serv.get_group_or_404(group_id)

            return self.project_repo.get_all_projects(group_id, limit, skip)

        except DatabaseError as e:
            logger.error(f"[project_service.get_all_projects] Error: {e}")
            raise

    async def get_user_in_project(
        self, group_id: int, project_id: int, limit: int, skip: int
    ):
        try:
            self.found_project_or_404(group_id, project_id)

            results = self.project_repo.get_users_in_project(project_id, limit, skip)

            if not results:
                logger.error(
                    f"[get_user_in_project] Users in Project {project_id} Error | Users not found in Project"
                )
                raise UsersNotFoundInProjectError(project_id=project_id)

            return results
        except DatabaseError as e:
            logger.error(f"[project_service.get_users_in_project] Error: {e}")
            raise

    async def create_project(self, group_id: int, user_id: int, project: CreateProject):
        try:
            self.group_serv.get_group_or_404(group_id)

            new_project = self.project_repo.create(group_id, user_id, project)

            return new_project
        except DatabaseError as e:
            logger.error(f"[project_service.create_project] Error: {e}")
            raise

    async def update_project(
        self, group_id: int, project_id: int, update_project: UpdateProject
    ):
        try:
            found_project = self.found_project_or_404(group_id, project_id)

            self.project_repo.update(found_project, update_project)

            return {"detail": "Se ha actualizado la informacion del projecto"}

        except DatabaseError as e:
            logger.error(f"[project_service.create_project] Error: {e}")
            raise
        except Exception:
            raise

    async def delete_project(self, group_id: int, project_id: int):
        try:
            found_project = self.found_project_or_404(group_id, project_id)

            self.project_repo.delete(found_project)

            return {"detail": "Se ha eliminado el proyecto"}

        except DatabaseError as e:
            logger.error(f"[project_service.delete_project] Error: {e}")
            raise
        except Exception:
            raise

    async def add_user(self, group_id: int, project_id: int, user_id: int):
        try:
            project = self.found_project_or_404(group_id, project_id)

            user = self.user_serv.get_user_or_404(user_id)

            group = self.group_serv.get_group_or_404(group_id)

            if user not in group.users:
                logger.error(
                    f"[add_user_to_project] Add user to Project Error | Error User {user_id} not exist in Group {group_id}"
                )
                raise UserNotInGroupError(user_id=user_id, group_id=group_id)

            if user in project.users:
                logger.error(
                    f"[add_user_to_project] Add user to Project Error | Error User {user_id} exists in Proyect {project_id}"
                )
                raise UserInProjectError(user_id=user_id, project_id=project_id)

            self.project_repo.add_user(project_id, user_id)

            outgoing_event_json = format_notification(
                notification_type="add_user_to_project",
                message=f"You were added to the project {project_id}",
            )

            # Envia el evento
            await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

            return {"detail": "El usuario ha sido agregado al proyecto"}

        except DatabaseError as e:
            logger.error(f"[project_service.add_user] Error: {e}")
            raise
        except Exception:
            raise

    async def remove_user(self, group_id: int, project_id: int, user_id: int):
        try:
            project = self.found_project_or_404(group_id, project_id)

            user = self.user_serv.get_user_or_404(user_id)

            group = self.group_serv.get_group_or_404(group_id)

            if user not in group.users:
                logger.error(
                    f"[remove_user_from_project] Remove User to Project Error | User {user_id} not exist in Group {group_id}"
                )
                raise UserNotInGroupError(user_id=user_id, group_id=group_id)

            if user in project.users:
                user_ = self.project_repo.get_user_in_project(project_id, user_id)
                self.project_repo.remove_user(user_)

                outgoing_event_json = format_notification(
                    notification_type="delete_user_from_project",
                    message=f"You were deleted from the project {project_id}",
                )

                # Envia el evento
                await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

                return {"detail": "El usuario ha sido eliminado del proyecto"}
            else:
                logger.error(
                    f"[remove_user_from_project] Delete User to Project Error | User {user_id} not exists in Project {project_id}"
                )
                raise UserNotInProjectError(user_id=user_id, project_id=project_id)

        except DatabaseError as e:
            logger.error(f"[project_service.remove_user_from_project] Error: {e}")
            raise
        except Exception:
            raise

    async def update_user_permission_in_project(
        self,
        group_id: int,
        project_id: int,
        user_id: int,
        permission: UpdatePermissionUser,
    ):
        try:
            self.found_project_or_404(group_id, project_id)

            user = self.project_repo.get_user_in_project(project_id, user_id)

            if not user:
                logger.error(
                    f"[update_user_permission_in_project] User {user_id} not exists in proyect {project_id}"
                )
                raise UserNotInProjectError(project_id=project_id, user_id=user_id)

            user = self.project_repo.update_permission(user, permission)

            outgoing_event_json = format_notification(
                notification_type="permission_update",
                message=f"Permissions of the project {project_id} were updated to {user.permission.value}",
            )

            await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

            return {"detail": "Se ha cambiado los permisos del usuario en el proyecto"}

        except DatabaseError as e:
            logger.error(
                f"[project_service.update_user_permission_in_project] Error: {e}"
            )
            raise
        except Exception:
            raise
