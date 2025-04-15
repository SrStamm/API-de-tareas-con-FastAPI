from pydantic import BaseModel, Field, EmailStr
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

    class Config:
        orm_mode = True

class ReadGroupUser(BaseModel):
    user_id: int
    username: str
    role: Group_Role

    class Config:
        orm_mode = True

class ReadProjectUser(BaseModel):
    user_id: int
    username: str
    permission: Project_Permission

    class Config:
        orm_mode = True    
class CreateTask(BaseModel):
    description: str
    date_exp: dt

class ReadTask(BaseModel):
    task_id: int
    description: str
    date_exp: dt
    state: State
    project_id: int

    class Config:
        orm_mode = True

class UpdateTask(BaseModel):
    description: str | None = None
    date_exp: dt | None = None
    state: State | None = None

class CreateGroup(BaseModel):
    name: str 
    description: str | None = Field(default=None)

class ReadGroup(BaseModel):
    group_id: int
    name: str 
    description: str | None = Field(default=None)
    users: List[ReadUser]

    class Config:
        orm_mode = True

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

    class Config:
        orm_mode = True

class UpdateProject(BaseModel):
    title: str | None = None
    description: str | None = None

class Token(BaseModel):
    access_token: str
    token_type: str