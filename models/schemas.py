from pydantic import BaseModel, Field, EmailStr, ConfigDict
from fastapi import WebSocket
from typing import List, Optional
from datetime import datetime as dt, timezone
from .db_models import State, Group_Role, Project_Permission


class CreateUser(BaseModel):
    username: str
    email: EmailStr
    password: str

class UpdateUser(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    password: str | None = None

class UpdateRoleUser(BaseModel):
    role: Group_Role | None = None

class UpdatePermissionUser(BaseModel):
    permission: Project_Permission | None = None    
class ReadUser(BaseModel):
    user_id: int
    username: str

    model_config = ConfigDict(from_attributes=True)

class ReadGroupUser(BaseModel):
    user_id: int
    username: str
    role: Group_Role

    model_config = ConfigDict(from_attributes=True)

class ReadProjectUser(BaseModel):
    user_id: int
    username: str
    permission: Project_Permission

    model_config = ConfigDict(from_attributes=True)
class CreateTask(BaseModel):
    description: str
    date_exp: dt
    user_ids: List[int]

class AsignUser(BaseModel):
    users: int | List[int] = int

class ReadTask(BaseModel):
    task_id: int
    description: str
    date_exp: dt
    state: State
    project_id: int

    model_config = ConfigDict(from_attributes=True)

class ReadTaskInProject(BaseModel):
    task_id: int
    description: str
    date_exp: dt
    state: State
    asigned: List[ReadUser]

    model_config = ConfigDict(from_attributes=True)

class UpdateTask(BaseModel):
    description: str | None = None
    date_exp: dt | None = None
    state: State | None = None
    append_user_ids: Optional[List[int]] = None
    exclude_user_ids: Optional[List[int]] = None

class CreateGroup(BaseModel):
    name: str 
    description: str | None = Field(default=None)

class ReadGroup(BaseModel):
    group_id: int
    name: str 
    description: str | None = Field(default=None)
    users: List[ReadUser]

    model_config = ConfigDict(from_attributes=True)

class ReadBasicDataGroup(BaseModel):
    group_id: int
    name: str
    users: List[ReadUser]
class UpdateGroup(BaseModel):
    name: str | None = None
    description: str | None = None

class CreateProject(BaseModel):
    title: str 
    description: str | None = Field(default=None)

class ReadProject(BaseModel):
    project_id: int
    group_id: int
    title: str
    description: str | None
    users: List[ReadUser]

    model_config = ConfigDict(from_attributes=True)

class UpdateProject(BaseModel):
    title: str | None = None
    description: str | None = None

class Token(BaseModel):
    access_token: str
    token_type: str

class Message(BaseModel):
    content: str
    user_id: int
    project_id: int
    timestamp: dt
