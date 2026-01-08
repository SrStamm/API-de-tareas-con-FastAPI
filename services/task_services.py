from fastapi import HTTPException
from repositories.task_repositories import TaskRepository
from services import project_services
from models.db_models import TypeOfLabel, State, Project_Permission, User
from models.schemas import CreateTask, UpdateTask
from models.exceptions import (
    DatabaseError,
    NotAuthorized,
    TaskNotFound,
    TaskIsAssignedError,
    TaskIsNotAssignedError,
)
from db.database import IntegrityError
from typing import List
from core.logger import logger
from core.event_ws import format_notification
from core.socket_manager import manager


class TaskService:
    def __init__(
        self,
        task_repo: TaskRepository,
        user_ser: project_services.UserService,
        proj_ser: project_services.ProjectService,
    ):
        self.task_repo = task_repo
        self.user_ser = user_ser
        self.proj_ser = proj_ser

    def found_task_or_404(self, project_id: int, task_id: int):
        task_found = self.task_repo.get_task_by_id(task_id, project_id)

        if not task_found:
            logger.error(f"Task {task_id} no encontrado en Project {project_id}")
            raise TaskNotFound(task_id=task_id, project_id=project_id)

        return task_found

    def found_user_assigned_to_task(self, task_id: int, user_id: int):
        user = self.task_repo.get_task_is_asigned(task_id=task_id, user_id=user_id)

        if not user:
            raise TaskIsNotAssignedError(task_id=task_id, user_id=user_id)
        return user

    def validate_in_task(self, users: List[User], task_id: int):
        return self.task_repo.validate_in_task(users, task_id)

    async def get_all_task_for_user(
        self,
        user_id: int,
        limit: int,
        skip: int,
        labels: List[TypeOfLabel] | None = None,
        state: List[State] | None = None,
    ):
        try:
            return self.task_repo.get_all_task_for_user(
                user_id, limit, skip, labels, state
            )

        except DatabaseError as e:
            logger.error(f"[TaskService.get_all_task_for_user] Error: {e}")
            raise

    async def get_users_for_task(self, task_id: int, limit: int, skip: int):
        try:
            return self.task_repo.get_user_for_task(task_id, limit, skip)
        except DatabaseError as e:
            logger.error(f"[TaskService.get_user_for_task] Error: {e}")
            raise

    async def get_all_task_for_project(
        self,
        project_id: int,
        limit: int,
        skip: int,
        labels: List[TypeOfLabel] | None,
        state: List[State] | None,
    ):
        try:
            return self.task_repo.get_all_task_to_project(
                project_id, limit, skip, labels, state
            )

        except DatabaseError as e:
            logger.error(f"[TaskService.get_all_task_for_project] Error: {e}")
            raise

    async def create(self, task: CreateTask, project_id: int):
        try:
            if task.user_ids:
                for user_id in task.user_ids:
                    self.user_ser.get_user_or_404(user_id)

                    self.proj_ser.found_user_in_project_or_404(user_id, project_id)

            new_task = self.task_repo.create(project_id, task)

            for user_id in task.user_ids:
                outgoing_event_json = format_notification(
                    notification_type="assigned_task",
                    message=f"You are assigned to the task {new_task.task_id} in project {project_id}",
                )

                # Envia el evento
                await manager.send_to_user(message=outgoing_event_json, user_id=user_id)

            return {
                "detail": "A new task has been created and users have been successusfully assigned"
            }
        except DatabaseError as e:
            logger.error(f"[TaskService.create] Error: {e}")
            raise
        except Exception:
            raise

    async def delete(self, task_id: int, project_id: int):
        try:
            task = self.found_task_or_404(project_id, task_id)

            self.task_repo.delete(task)

            return {"detail": "Task successfully deleted"}

        except DatabaseError as e:
            logger.error(f"[TaskService.delete] Error: {e}")
            raise
        except Exception:
            raise

    async def update_task(
        self,
        task_id: int,
        project_id: int,
        update_task: UpdateTask,
        user: User,
        permission: Project_Permission,
    ):
        try:
            task = self.found_task_or_404(task_id=task_id, project_id=project_id)

            self.task_repo.update(update_task, task)

            if update_task.append_user_ids:
                if permission == "admin":
                    for user_id in update_task.append_user_ids:
                        user = self.user_ser.get_user_or_404(user_id)

                        self.proj_ser.found_user_in_project_or_404(user_id, project_id)

                        user_in_task = self.task_repo.get_task_is_asigned(
                            task_id=task_id, user_id=user_id
                        )

                        if user_in_task:
                            logger.error(
                                f"[update_task] User {user_id} was already assigned to task {task_id}"
                            )
                            raise TaskIsAssignedError(user_id=user_id, task_id=task_id)

                        self.task_repo.add_user(user_id, task_id)

                else:
                    logger.error(
                        f"[update_task] Unauthorized | User {user.user_id} not authorized for this action"
                    )
                    raise NotAuthorized(user.user_id)

            if update_task.exclude_user_ids:
                if permission == "admin":
                    for user_id in update_task.exclude_user_ids:
                        user_in_task = self.task_repo.get_task_is_asigned(
                            task_id, user_id
                        )

                        if not user_in_task:
                            logger.error(
                                f"[update_task] Update Task Error | User {user_id} not assigned to task {task_id}"
                            )
                            raise TaskIsNotAssignedError(
                                user_id=user_id, task_id=task_id
                            )

                        self.task_repo.remove_user(user_in_task)

                else:
                    logger.error(
                        f"[update_task] Unauthorized | User {user.user_id} not authorized for this action"
                    )
                    raise NotAuthorized(user.user_id)

            if update_task.append_label:
                if permission in ("admin", "editor"):
                    existing_labels_for_task = self.task_repo.get_labels_for_task(
                        task_id
                    )
                    new_labels = []

                    for label_to_append in update_task.append_label:
                        if label_to_append in existing_labels_for_task:
                            logger.warning(
                                f"[update_task] Label {label_to_append.value} already exists for Task {task_id}. Skipping"
                            )
                        else:
                            new_labels.append(label_to_append)

                    if new_labels:
                        try:
                            for label in new_labels:
                                self.task_repo.add_label(task_id, label)

                        except IntegrityError as e:
                            logger.error(
                                f"[update_task] Database Integrity Error when adding labbels | Error: {str(e)}"
                            )
                            raise HTTPException(
                                status_code=409,
                                detail="Failed to add labels due to database conflict (label might already exist).",
                            )
                        except Exception as e:
                            logger.error(
                                f"[update_task] Error adding labels | Error: {str(e)}"
                            )

            if update_task.remove_label:
                if permission in ("admin", "editor"):
                    existing_labels_for_task = self.task_repo.get_labels_for_task(
                        task_id
                    )
                    try:
                        for label_to_remove in update_task.remove_label:
                            if label_to_remove in existing_labels_for_task:
                                label = self.task_repo.get_label_for_task_by_label(
                                    task_id, label_to_remove
                                )
                                self.task_repo.delete_label(label)
                            else:
                                logger.warning(
                                    f"[update_task] Label {label_to_remove.value} not exists for Task {task_id}. Skipping"
                                )

                    except IntegrityError as e:
                        logger.error(
                            f"[update_task] Database Integrity Error when removing labbels | Error: {str(e)}"
                        )
                        raise HTTPException(
                            status_code=409,
                            detail="Failed to remove labels due to database conflict (label might already exist).",
                        )
                    except Exception as e:
                        logger.error(
                            f"[update_task] Error removing labels | Error: {str(e)}"
                        )

            task = self.task_repo.get_task_by_id(task_id, project_id)

            if update_task.append_user_ids:
                for user_id in update_task.append_user_ids:
                    outgoing_event_json = format_notification(
                        notification_type="assigned_task",
                        message=f"You were assigned to the task {task_id} in the project {project_id}",
                    )
                    await manager.send_to_user(
                        message=outgoing_event_json, user_id=user_id
                    )

            if update_task.exclude_user_ids:
                for user_id in update_task.exclude_user_ids:
                    outgoing_event_json = format_notification(
                        notification_type="assigned_task",
                        message=f"You are no longer assigned to the task {task_id} in project {project_id}",
                    )

                    await manager.send_to_user(
                        message=outgoing_event_json, user_id=user_id
                    )

            return {"detail": "A task has been successfully updated"}

        except DatabaseError as e:
            logger.error(f"[TaskService.update_task] Error: {e}")
            raise
        except Exception:
            raise
