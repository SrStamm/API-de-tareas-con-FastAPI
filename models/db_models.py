# from __future__ import annotations # Comentado temporalmente para diagnóstico

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy.orm import Mapped
from datetime import datetime as dt, timezone
from enum import Enum
from typing import Optional, List # Asegúrate que List está importado
from pydantic import EmailStr


class State(str, Enum):
    COMPLETADO = 'completado'
    EN_PROCESO = 'en proceso'
    CANCELADO = 'cancelado'
    SIN_EMPEZAR = 'sin empezar'


class Group_Role(str, Enum):
    ADMIN = 'admin'
    EDITOR = 'editor'
    MEMBER = 'member'


class Project_Permission(str, Enum):
    ADMIN = 'admin'
    WRITE = 'write'
    READ = 'read'


class group_user(SQLModel, table=True):
    group_id: int = Field(primary_key=True, foreign_key='group.group_id')
    user_id: int = Field(primary_key=True, foreign_key='user.user_id')
    role: Group_Role = Field(default=Group_Role.MEMBER)


class project_user(SQLModel, table=True):
    project_id: int = Field(primary_key=True, foreign_key='project.project_id')
    user_id: int = Field(primary_key=True, foreign_key='user.user_id')
    permission: Project_Permission = Field(default=Project_Permission.WRITE)

class tasks_user(SQLModel, table=True):
    task_id: int = Field(primary_key=True, foreign_key='task.task_id')
    user_id: int = Field(primary_key=True, foreign_key='user.user_id')


class Group(SQLModel, table=True):
    __tablename__ = 'group' # Añadido por si acaso, aunque SQLModel suele inferirlo
    group_id: Optional[int] = Field(default=None, primary_key=True) # Asegúrate que default=None si es autoincremental
    name: str
    description: str | None = Field(default=None)
    date_at: dt = Field(default_factory=lambda: dt.now(timezone.utc))

    # La anotación de tipo es Mapped[List["User"]]
    # Relationship infiere 'User' de la anotación.
    users: Mapped[List["User"]] = Relationship(back_populates='groups', link_model=group_user)

class Project(SQLModel, table=True):
    project_id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key='group.group_id', index=True)
    title: str
    description: str | None = Field(default=None)
    date_at: dt = Field(default_factory=lambda: dt.now(timezone.utc))

    users: Mapped[List["User"]] = Relationship(back_populates='projects', link_model=project_user)
    tasks: Mapped[List["Task"]] = Relationship(back_populates='project')
    chats: Mapped[List["ProjectChat"]] = Relationship(back_populates='project')

class User(SQLModel, table=True):
    user_id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: EmailStr
    password: str # Recuerda que esto debería estar hasheado
    created: dt = Field(default_factory=lambda: dt.now(timezone.utc))

    groups: Mapped[List["Group"]] = Relationship(back_populates='users', link_model=group_user)
    projects: Mapped[List["Project"]] = Relationship(back_populates='users', link_model=project_user)
    tasks_asigned: Mapped[List["Task"]] = Relationship(back_populates='asigned', link_model=tasks_user)

class Task(SQLModel, table=True):
    task_id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key='project.project_id', index=True)
    description: str | None = Field(default=None)
    date_exp: dt
    state: State = Field(default=State.SIN_EMPEZAR)

    asigned: Mapped[List["User"]] = Relationship(back_populates='tasks_asigned', link_model=tasks_user)
    project: Mapped[Optional["Project"]] = Relationship(back_populates='tasks') # Mapped añadido para consistencia


class ProjectChat(SQLModel, table=True):
    chat_id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key='project.project_id', index=True)
    user_id: int = Field(foreign_key='user.user_id', index=True)
    message: str
    timestamp: dt = Field(default_factory=lambda: dt.now(timezone.utc))

    project: Mapped[Optional["Project"]] = Relationship(back_populates='chats')
