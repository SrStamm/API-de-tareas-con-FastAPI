from models.db_models import Project, project_user, Project_Permission, User
from models.schemas import CreateProject, UpdateProject
from db.database import Session, select, selectinload

class ProjectRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_project_by_id(self, group_id: int, project_id: int)  -> Project:
        stmt = (select(Project)
                .options(selectinload(Project.users))
                .where(
                    Project.group_id == group_id,
                    Project.project_id == project_id
                ))
        return self.session.exec(stmt).first()

    def get_user_in_project(self, project_id: int, user_id: int) -> project_user:
        stmt = (select(project_user).where(
            project_user.user_id == user_id,
            project_user.project_id == project_id 
        ))
        return self.session.exec(stmt).first()

    def get_all_project_by_user(self, user_id: int, limit: int, skip: int):
        stmt = (select(Project.project_id, Project.group_id, Project.title)
                .where(
                    Project.project_id == project_user.project_id,
                    project_user.user_id == user_id)
                .limit(limit).offset(skip))
        return self.session.exec(stmt).all()

    def get_all_projects(self, group_id: int, limit: int, skip: int):
        stmt = (select(Project)
                    .options(selectinload(Project.users))
                    .where(Project.group_id == group_id)
                    .limit(limit).offset(skip))
        return self.session.exec(stmt).all()

    def get_users_in_project(self, project_id: int, limit: int, skip: int):
        stmt = (select(User.user_id, User.username, project_user.permission)
                .join(project_user, project_user.user_id == User.user_id)
                    .where(project_user.project_id == project_id)
                    .limit(limit).offset(skip))
        return self.session.exec(stmt).all()

    def create(self, group_id: int, user_id: int, project: CreateProject):
        try:
            new_project = Project(**project.model_dump(), group_id=group_id)
            self.session.add(new_project)
            self.session.flush()

            admin = project_user(
                project_id=new_project.project_id,
                user_id=user_id,
                permission=Project_Permission.ADMIN
            )

            self.session.add(admin)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def update(self, found_project: Project, update_project: UpdateProject):
        try:
            if found_project.title != update_project.title and update_project.title is not None:
                found_project.title = update_project.title

            if found_project.description != update_project.description and update_project.description is not None:
                found_project.description = update_project.description

            self.session.commit()
            return
        except Exception:
            self.session.rollback()
            raise

    def delete(self, project: Project):
        try:
            self.session.delete(project)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def add_user(self, project_id: int, user_id: int):
        try:
            new_user = project_user(
                project_id=project_id,
                user_id=user_id
            )
            self.session.add(new_user)
            self.session.commit()
            return
        except Exception:
            self.session.rollback()
            raise

    def remove_user(self, user: project_user):
        try:
            self.session.delete(user)
            self.session.commit()
            return
        except Exception:
            self.session.rollback()
            raise

    def update_permission(self, user: project_user, permission: Project_Permission):
        try:
            user.permission == permission
            self.session.commit()
            self.session.refresh(user)
            return user
        except Exception:
            self.session.rollback()
            raise