from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime
from db_models import User, Task, State


class CreateUser(BaseModel):
    username: str
    email: EmailStr
    password: str

class UpdateUser(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    password: str | None = None

class ReadUser(BaseModel):
    user_id: int
    username: str

    class Config:
        orm_mode = True

class CreateTask(BaseModel):
    description: str
    date_exp: datetime

class ReadTask(BaseModel):
    task_id: int
    description: str
    date_exp: datetime
    state: State

    class Config:
        orm_mode = True

class UpdateTask(BaseModel):
    description: Optional[str]
    date_exp: Optional[datetime]
    state: Optional[State]

class CreateGroup(BaseModel):
    name: str 
    description: str | None = Field(default=None)
    date_at: datetime = Field(default_factory=datetime.now(datetime.timezone.utc))

class ReadGroup(BaseModel):
    group_id: int
    name: str 
    description: str | None = Field(default=None)
    users: List[ReadUser]

    class Config:
        orm_mode = True

class UpdateGroup(BaseModel):
    name: str 
    description: str | None = Field(default=None)

class CreateProject(BaseModel):
    title: str 
    description: str | None = Field(default=None)

class ReadProject(BaseModel):
    project_id: int
    title: str
    description: str
    tasks: List[ReadTask]
    users: List[ReadUser]

    class Config:
        orm_mode = True

class UpdateProject(BaseModel):
    title: str | None = Field(default=None)
    description: str | None = Field(default=None)