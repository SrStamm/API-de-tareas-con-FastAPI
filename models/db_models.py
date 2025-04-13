from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime  as dt, timezone
from enum import Enum
from typing import Optional, List
from pydantic import EmailStr

class State(str, Enum):
    COMPLETADO = 'completado'
    EN_PROCESO = 'en proceso'
    CANCELADO = 'cancelado'
    SIN_EMPEZAR = 'sin empezar'

class group_user(SQLModel, table=True):
    group_id: int = Field(primary_key=True, foreign_key='group.group_id')
    user_id: int = Field(primary_key=True, foreign_key='user.user_id')
    
class project_user(SQLModel, table=True):
    project_id: int = Field(primary_key=True, foreign_key='project.project_id')
    user_id: int = Field(primary_key=True, foreign_key='user.user_id')
    
class tasks_user(SQLModel, table=True):
    task_id: int = Field(primary_key=True, foreign_key='task.task_id')
    user_id: int = Field(primary_key=True, foreign_key='user.user_id')

class Group(SQLModel, table=True):
    group_id: Optional[int] = Field(primary_key=True)
    name: str 
    description: str | None = Field(default=None)
    date_at: dt = Field(default_factory=lambda: dt.now(timezone.utc))

    users: List['User'] = Relationship(back_populates='groups', link_model=group_user)

class Project(SQLModel, table=True):
    project_id: Optional[int] = Field(primary_key=True)
    group_id: int = Field(foreign_key='group.group_id')
    title: str 
    description: str | None = Field(default=None)
    date_at: dt = Field(default_factory=lambda: dt.now(timezone.utc))

    users: List['User'] = Relationship(back_populates='projects', link_model=project_user)
    tasks: List['Task'] = Relationship(back_populates='project')

class User(SQLModel, table=True):
    user_id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: EmailStr
    password: str
    created: dt = Field(default_factory=lambda: dt.now(timezone.utc))

    groups: List['Group'] = Relationship(back_populates='users', link_model=group_user)
    projects: List['Project'] = Relationship(back_populates='users', link_model=project_user)
    tasks_asigned: List['Task'] = Relationship(back_populates='asigned', link_model=tasks_user)

class Task(SQLModel, table=True):
    task_id: Optional[int] = Field(primary_key=True)
    project_id: int = Field(foreign_key='project.project_id')
    description: str | None = Field(default=None)
    date_exp: dt
    state: State = Field(default=State.SIN_EMPEZAR)
    
    asigned: List['User'] = Relationship(back_populates='tasks_asigned', link_model=tasks_user)
    project: Optional['Project'] = Relationship(back_populates='tasks')