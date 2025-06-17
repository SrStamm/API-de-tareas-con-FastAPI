from models.exceptions import DatabaseError
from models.schemas import ReadTask, CreateTask, UpdateTask
from models.db_models import (
    Task,
    tasks_user,
    TypeOfLabel,
    State,
    TaskLabelLink,
    User,
    project_user,
)
from db.database import Session, select, joinedload, func, SQLAlchemyError
from typing import List
from core.logger import logger


class TaskRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_task_by_id(self, task_id: int, project_id: int):
        try:
            stmt = select(Task).where(
                Task.project_id == project_id, Task.task_id == task_id
            )
            return self.session.exec(stmt).first()
        except SQLAlchemyError as e:
            logger.error(f"[TaskRepository.get_task_by_id] Error: {e}")
            raise DatabaseError(e, "get_task_by_id")

    def get_task_is_asigned(self, task_id: int, user_id: int):
        try:
            stmt = select(tasks_user).where(
                tasks_user.user_id == user_id, tasks_user.task_id == task_id
            )
            return self.session.exec(stmt).first()

        except SQLAlchemyError as e:
            logger.error(f"[TaskRepository.get_task_by_id] Error: {e}")
            raise DatabaseError(e, "get_task_is_asigned")

    def get_labels_for_task(self, task_id: int):
        try:
            stmt = select(TaskLabelLink.label).where(TaskLabelLink.task_id == task_id)
            return set(self.session.exec(stmt).all())
        except SQLAlchemyError as e:
            logger.error(f"[TaskRepository.get_labels_for_task] Error: {e}")
            raise DatabaseError(e, "get_labels_for_task")

    def get_label_for_task_by_label(self, task_id: int, label: TypeOfLabel):
        try:
            stmt = select(TaskLabelLink.label).where(
                TaskLabelLink.task_id == task_id, TaskLabelLink.label == label
            )
            return self.session.exec(stmt).first()

        except SQLAlchemyError as e:
            logger.error(f"[TaskRepository.get_label_for_task_by_label] Error: {e}")
            raise DatabaseError(e, "get_label_for_task_by_label")

    def get_all_task_for_user(
        self,
        user_id: int,
        limit: int,
        skip: int,
        labels: List[TypeOfLabel] | None = None,
        state: List[State] | None = None,
    ) -> List[ReadTask]:
        try:
            stmt = (
                select(Task)
                .join(tasks_user, Task.task_id == tasks_user.task_id)
                .where(tasks_user.user_id == user_id)
                .options(joinedload(Task.task_label_links))
            )

            if labels:
                stmt = (
                    stmt.join(TaskLabelLink, Task.task_id == TaskLabelLink.task_id)
                    .where(TaskLabelLink.label.in_(labels))
                    .group_by(Task.task_id)
                    .having(func.count(TaskLabelLink.label.distinct()) == len(labels))
                )

            if state:
                stmt = stmt.where(Task.state.in_(state))

            return self.session.exec(stmt.limit(limit).offset(skip)).unique().all()

        except SQLAlchemyError as e:
            logger.error(f"[TaskRepository.get_all_task_for_user] Error: {e}")
            raise DatabaseError(e, "get_all_task_for_user")

    def get_all_task_to_project(
        self,
        project_id: int,
        user_id: int,
        limit: int,
        skip: int,
        labels: List[TypeOfLabel] | None,
        state: List[State] | None,
    ):
        try:
            stmt = (
                select(Task)
                .join(tasks_user, tasks_user.task_id == Task.task_id)
                .join(project_user, project_user.project_id == Task.project_id)
                .where(
                    project_user.project_id == project_id,
                    project_user.user_id == user_id
                )
                .options(joinedload(Task.asigned))
            )

            if labels:
                stmt = (
                    stmt.join(TaskLabelLink, Task.task_id == TaskLabelLink.task_id)
                    .where(TaskLabelLink.label.in_(labels))
                    .group_by(Task.task_id)
                    .having(func.count(TaskLabelLink.label.distinct()) == len(labels))
                )

            if state:
                stmt = stmt.where(Task.state.in_(state))

            return self.session.exec(stmt.limit(limit).offset(skip)).unique().all()

        except SQLAlchemyError as e:
            logger.error(f"[TaskRepository.get_all_task_to_project] Error: {e}")
            raise DatabaseError(e, "get_all_task_to_project")

    def get_user_for_task(self, task_id: int, limit: int, skip: int):
        try:
            stmt = (
                select(User.user_id, User.username)
                .join(tasks_user, tasks_user.user_id == User.user_id)
                .where(tasks_user.task_id == task_id)
                .limit(limit)
                .offset(skip)
            )
            return self.session.exec(stmt).all()

        except SQLAlchemyError as e:
            logger.error(f"[TaskRepository.get_user_for_task] Error: {e}")
            raise DatabaseError(e, "get_user_for_task")

    def validate_in_task(self, users: List[User], task_id: int):
        try:
            stmt = select(User.username, User.user_id).where(
                tasks_user.user_id == User.user_id,
                tasks_user.task_id == task_id,
                User.username.in_(users),
            )

            return self.session.exec(stmt).all()

        except SQLAlchemyError as e:
            logger.error(f"[TaskRepository.validate_in_task] Error: {e}")
            raise DatabaseError(e, "validate_in_task")

    def create(self, project_id: int, task: CreateTask) -> Task:
        try:
            new_task = Task(
                project_id=project_id,
                description=task.description,
                date_exp=task.date_exp,
            )

            self.session.add(new_task)
            self.session.commit()
            self.session.refresh(new_task)

            if task.label:
                for lb in task.label:
                    label = TaskLabelLink(task_id=new_task.task_id, label=lb.value)

                    self.session.add(label)

            for user_id in task.user_ids:
                task_user = tasks_user(task_id=new_task.task_id, user_id=user_id)
                self.session.add(task_user)
            self.session.commit()
            return new_task
        except SQLAlchemyError as e:
            logger.error(f"[TaskRepository.create] Error: {e}")
            raise DatabaseError(e, "create")
        except Exception:
            self.session.rollback()
            raise

    def update(self, update_task: UpdateTask, task: Task):
        try:
            if update_task.description != task.description and update_task.description:
                task.description = update_task.description
            if update_task.date_exp != task.date_exp and update_task.date_exp:
                task.date_exp = update_task.date_exp
            if task.state != update_task.state and update_task.state:
                task.state = update_task.state
            self.session.commit()
            return
        except SQLAlchemyError as e:
            logger.error(f"[TaskRepository.update] Error: {e}")
            raise DatabaseError(e, "update")
        except Exception:
            self.session.rollback()
            raise

    def delete(self, task: Task):
        try:
            self.session.delete(task)
            self.session.commit()
            return
        except SQLAlchemyError as e:
            logger.error(f"[TaskRepository.delete] Error: {e}")
            self.session.rollback()
            raise DatabaseError(e, "delete")
        except Exception:
            self.session.rollback()
            raise

    def add_user(self, user_id: int, task_id: int):
        try:
            new_user = tasks_user(user_id=user_id, task_id=task_id)
            self.session.add(new_user)
            self.session.commit()
            return
        except SQLAlchemyError as e:
            logger.error(f"[TaskRepository.add_user] Error: {e}")
            self.session.rollback()
            raise DatabaseError(e, "add_user")
        except Exception:
            self.session.rollback()
            raise

    def remove_user(self, user: tasks_user):
        try:
            self.session.delete(user)
            self.session.commit()
            return
        except SQLAlchemyError as e:
            logger.error(f"[TaskRepository.remove_user] Error: {e}")
            self.session.rollback()
            raise DatabaseError(e, "remove_user")
        except Exception:
            self.session.rollback()
            raise

    def add_label(self, task_id: int, label: TypeOfLabel):
        try:
            new_label = TaskLabelLink(task_id=task_id, label=label)
            self.session.add(new_label)
            self.session.commit()
            return
        except SQLAlchemyError as e:
            logger.error(f"[TaskRepository.add_label] Error: {e}")
            self.session.rollback()
            raise DatabaseError(e, "add_label")
        except Exception:
            self.session.rollback()
            raise

    def delete_label(self, label: TaskLabelLink):
        try:
            self.session.delete(label)
            self.session.commit()
            return
        except SQLAlchemyError as e:
            logger.error(f"[TaskRepository.delete_label] Error: {e}")
            self.session.rollback()
            raise DatabaseError(e, "delete")
        except Exception:
            self.session.rollback()
            raise
