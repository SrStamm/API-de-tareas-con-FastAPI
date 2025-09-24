from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy.orm import Mapped
from datetime import datetime as dt, timezone
from enum import Enum
from typing import Optional, List
from pydantic import EmailStr


class State(str, Enum):
    COMPLETADO = "completado"
    EN_PROCESO = "en proceso"
    CANCELADO = "cancelado"
    SIN_EMPEZAR = "sin empezar"


class Notify_State(str, Enum):
    ENVIADO = "enviado"
    SIN_ENVIAR = "sin enviar"


class TypeOfLabel(str, Enum):
    BUG = "bug"
    FEATURE = "feature"
    REFACTOR = "refactor"
    DOCS = "docs"
    TESTS = "tests"
    UI_UX = "ui/ux"

    URGENT = "urgent"
    HIGH_PRIORITY = "high_priority"
    MEDIUM_PRIORITY = "medium_priority"
    LOW_PRIORITY = "low_priority"
    BLOCKER = "blocker"

    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    API = "api"
    INFRASTRUCTURE = "infrastructure"


class Group_Role(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    MEMBER = "member"


class Project_Permission(str, Enum):
    ADMIN = "admin"
    WRITE = "write"
    READ = "read"


class group_user(SQLModel, table=True):
    group_id: int = Field(primary_key=True, foreign_key="group.group_id")
    user_id: int = Field(primary_key=True, foreign_key="user.user_id")
    role: Group_Role = Field(default=Group_Role.MEMBER)


class project_user(SQLModel, table=True):
    project_id: int = Field(primary_key=True, foreign_key="project.project_id")
    user_id: int = Field(primary_key=True, foreign_key="user.user_id")
    permission: Project_Permission = Field(default=Project_Permission.WRITE)


class tasks_user(SQLModel, table=True):
    task_id: int = Field(primary_key=True, foreign_key="task.task_id")
    user_id: int = Field(primary_key=True, foreign_key="user.user_id")


class TaskLabelLink(SQLModel, table=True):
    task_id: Optional[int] = Field(
        default=None, primary_key=True, foreign_key="task.task_id"
    )
    label: TypeOfLabel = Field(primary_key=True)

    task: Optional["Task"] = Relationship(back_populates="task_label_links")


class Group(SQLModel, table=True):
    __tablename__ = "group"
    group_id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str | None = Field(default=None)
    date_at: dt = Field(default_factory=lambda: dt.now(timezone.utc))

    users: Mapped[List["User"]] = Relationship(
        back_populates="groups", link_model=group_user
    )
    projects: Mapped[List["Project"]] = Relationship(
        back_populates="group", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class Project(SQLModel, table=True):
    project_id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="group.group_id", index=True)
    title: str
    description: str | None = Field(default=None)
    date_at: dt = Field(default_factory=lambda: dt.now(timezone.utc))

    users: Mapped[List["User"]] = Relationship(
        back_populates="projects", link_model=project_user
    )
    tasks: Mapped[List["Task"]] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    chats: Mapped[List["ProjectChat"]] = Relationship(back_populates="project")
    group: "Group" = Relationship(back_populates="projects")


class User(SQLModel, table=True):
    user_id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: EmailStr
    password: str
    created: dt = Field(default_factory=lambda: dt.now(timezone.utc))

    groups: Mapped[List["Group"]] = Relationship(
        back_populates="users", link_model=group_user
    )
    projects: Mapped[List["Project"]] = Relationship(
        back_populates="users", link_model=project_user
    )
    tasks_asigned: Mapped[List["Task"]] = Relationship(
        back_populates="asigned", link_model=tasks_user
    )
    comments: List["Task_comments"] = Relationship(back_populates="user")
    notifications: List["Notifications"] = Relationship(back_populates="user")


class Task(SQLModel, table=True):
    task_id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.project_id", index=True)
    title: str | None = Field(default=None)
    description: str | None = Field(default=None)
    date_exp: dt
    state: State = Field(default=State.SIN_EMPEZAR)

    asigned: Mapped[List["User"]] = Relationship(
        back_populates="tasks_asigned", link_model=tasks_user
    )
    project: Mapped[Optional["Project"]] = Relationship(back_populates="tasks")
    comments: List["Task_comments"] = Relationship(back_populates="task")
    task_label_links: List["TaskLabelLink"] = Relationship(
        back_populates="task", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class Task_comments(SQLModel, table=True):
    comment_id: Optional[int] = Field(primary_key=True, default=None)
    task_id: int = Field(foreign_key="task.task_id", index=True)
    user_id: int = Field(foreign_key="user.user_id", index=True)
    content: str = Field(max_length=300)
    created_at: dt = Field(default_factory=lambda: dt.now(timezone.utc))
    update_at: Optional[dt] = Field(
        description="Fecha de actualización de comentario",
        default_factory=lambda: dt.now(timezone.utc),
    )
    is_deleted: bool = Field(default=False)

    task: Optional["Task"] = Relationship(back_populates="comments")
    user: Optional["User"] = Relationship(back_populates="comments")


class ProjectChat(SQLModel, table=True):
    chat_id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.project_id", index=True)
    user_id: int = Field(foreign_key="user.user_id", index=True)
    message: str
    timestamp: dt = Field(default_factory=lambda: dt.now(timezone.utc))

    project: Mapped[Optional["Project"]] = Relationship(back_populates="chats")


class Session(SQLModel, table=True):
    jti: str = Field(primary_key=True, max_length=36)
    sub: str = Field(index=True)

    is_active: bool = Field(default=True)
    use_count: int = Field(default=0, ge=0)

    created_at: dt = Field(default_factory=lambda: dt.now(timezone.utc))
    expires_at: dt

    class Config:
        indexes = [("sub", "is_active")]


class Notifications(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.user_id", nullable=False)
    type: str = Field(nullable=True)
    payload: str = Field(nullable=True)
    status: Notify_State = Field(default_factory=Notify_State.SIN_ENVIAR)
    timestamp: dt = Field(default_factory=lambda: dt.now(timezone.utc))

    user: User = Relationship(back_populates="notifications")
