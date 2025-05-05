from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from fastapi import WebSocket
from typing import List, Optional
from datetime import datetime as dt, timezone
from .db_models import State, Group_Role, Project_Permission


class CreateUser(BaseModel):
    username: str = Field(examples=['User64'])
    email: EmailStr = Field(examples=['User@gmail.com'])
    password: str = Field(examples=['0ga0'])

class UpdateUser(BaseModel):
    username: str | None = Field(default=None, examples=['user64'])
    email: EmailStr | None = Field(default=None, examples=['newuser@email.com'])
    password: str | None = Field(default=None, examples=['asd5a51564'])

class UpdateRoleUser(BaseModel):
    role: Group_Role | None = Field(default=None, examples=[Group_Role.EDITOR, Group_Role.MEMBER])

class UpdatePermissionUser(BaseModel):
    permission: Project_Permission | None = Field(default=None, examples=[Project_Permission.READ, Project_Permission.WRITE])
class ReadUser(BaseModel):
    user_id: int = Field(examples=[1])
    username: str = Field(examples=['user5892'])

    model_config = ConfigDict(from_attributes=True)

class ReadGroupUser(BaseModel):
    user_id: int = Field(examples=[1])
    username: str = Field(examples=['User64'])
    role: Group_Role = Field(examples=['User@gmail.com'])

    model_config = ConfigDict(from_attributes=True)

class ReadProjectUser(BaseModel):
    user_id: int = Field(examples=[1])
    username: str = Field(examples=['User64'])
    permission: Project_Permission = Field(examples=[Project_Permission.WRITE])

    model_config = ConfigDict(from_attributes=True)
class CreateTask(BaseModel):
    description: str = Field(examples=['Actualizar la API'])
    date_exp: dt = Field(examples=['2025-10-28'])
    user_ids: List[int] = Field(examples=[[1,5,88]])

    @field_validator("date_exp")
    def date_exp_must_be_future(cls, value):
        if value <= dt.now():
            raise ValueError('La fechad expiración debe ser en el futuro.')
        return value

class AsignUser(BaseModel):
    users: int | List[int] = Field(examples=[[1, 5, 10]])

class ReadTask(BaseModel):
    task_id: int = Field(examples=[1])
    description: str = Field(examples=['Actualizar los datos'])
    date_exp: dt = Field(examples=['2025-10-24'])
    state: State = Field(examples=[State.EN_PROCESO])
    project_id: int = Field(examples=[1])

    model_config = ConfigDict(from_attributes=True)

class ReadTaskInProject(BaseModel):
    task_id: int = Field(examples=[1])
    description: str = Field(examples=[])
    date_exp: dt = Field(examples=[])
    state: State = Field(examples=[])
    asigned: List[ReadUser] = Field(examples=[[{'user_id':1, 'username':'user64'}, {'user_id':2, 'username':'user_falso'}]])

    model_config = ConfigDict(from_attributes=True)

class UpdateTask(BaseModel):
    description: str | None = Field(default=None, examples=['Eliminar los datos duplicados'])
    date_exp: dt | None = Field(default=None, examples=['2025-12-20'])
    state: State | None = Field(default=None, examples=[State.CANCELADO])
    append_user_ids: Optional[List[int]] = Field(default=None, examples=[1])
    exclude_user_ids: Optional[List[int]] = Field(default=None, examples=[1])

class CreateGroup(BaseModel):
    name: str = Field(examples=['Google'])
    description: str | None = Field(default=None, examples=['Somos un navegador Web'])

class ReadGroup(BaseModel):
    group_id: int = Field(examples=[1])
    name: str = Field(examples=['Facebook'])
    description: str | None = Field(default=None, examples=['Red Social'])
    users: List[ReadUser] = Field(examples=[[{'username':'user89', 'user_id':1},{'username':'user_falso', 'user_id':5}]])

    model_config = ConfigDict(from_attributes=True)

class ReadBasicDataGroup(BaseModel):
    group_id: int = Field(examples=[1])
    name: str = Field(examples=['Amazon'])
    users: List[ReadUser] = Field(examples=[[{'username':'user89', 'user_id':1},{'username':'user_falso', 'user_id':5}]])
class UpdateGroup(BaseModel):
    name: str | None = Field(default=None, examples=['AWS'])
    description: str | None = Field(default=None, examples=['Servicio en la Nube'])

class CreateProject(BaseModel):
    title: str = Field(examples=['Crear un nuevo Microservicio'])
    description: str | None = Field(default=None, examples=['Subida y bajada de archivos'])

class ReadProject(BaseModel):
    project_id: int = Field(examples=[1])
    group_id: int = Field(examples=[1])
    title: str = Field(examples=['TaskAPI'])
    description: str | None = Field(examples=['API que maneja tareas asignadas a usuarios'])
    users: List[ReadUser] = Field(examples=[[{'username':'user89', 'user_id':1},{'username':'user_falso', 'user_id':5}]])

    model_config = ConfigDict(from_attributes=True)

class ReadBasicProject(BaseModel):
    project_id: int = Field(examples=[1])
    group_id: int = Field(examples=[1])
    title: str = Field(examples=['TaskAPI'])
    
    model_config = ConfigDict(from_attributes=True)

class UpdateProject(BaseModel):
    title: str | None = Field(default=None, examples=['ChatRealTime'])
    description: str | None = Field(default=None, examples=['Chat en tiempo real que maneje millones de conexiones'])

class Token(BaseModel):
    access_token: str = Field(examples=[])
    token_type: str = Field(examples=['bearer'])

class Message(BaseModel):
    content: str = Field(examples=['Hola a todos!'])
    user_id: int = Field(examples=[1])
    project_id: int = Field(examples=[1])
    timestamp: dt = Field(examples=['2025-10-15 09:12:12'])

class UserCreateSucces(BaseModel):
    detail: str = Field(examples=['Se ha creado un nuevo usuario con exito'])

class UserUpdateSucces(BaseModel):
    detail: str = Field(examples=['Se ha actualizado el usuario con exito'])

class UserDeleteSucces(BaseModel):
    detail: str = Field(examples=['Se ha actualizado el usuario con exito'])

class UserConflictError(BaseModel):
    detail: str = Field(
        examples=[
            [
            "Ya existe un usuario con este Username",
            "Ya existe un usuario con este Email"
            ]
        ]
    )

class DataNotFound(BaseModel):
    detail: str = Field(examples=[  
        ['User whit user_id 1 not found',
        'Chat whit project_id 2 not found',
        'Project whit project_id 2 not found',
        'Group whit group_id 1 not found']])

class ErrorInRequest(BaseModel):
    detail: str = Field(examples=[
        ['User whit user_id 1 is in project with project_id 1',
        'User whit user_id 1 is not in project with project_id 1',
        'User whit user_id 1 is in Group with group_id 1',
        'User whit user_id 1 is not in Group with group_id 1']])
class TaskCreateSucces(BaseModel):
    detail: str = Field(examples=['Se ha creado una nueva tarea y asignado los usuarios con exito'])

class TaskUpdateSucces(BaseModel):
    detail: str = Field(examples=['Se ha actualizado la tarea'])

class TaskDeleteSucces(BaseModel):
    detail: str = Field(examples=['Se ha eliminado la tarea'])

class ProjectCreateSucces(BaseModel):
    detail: str = Field(examples=['Se ha creado un nuevo proyecto de forma exitosa'])

class ProjectUpdateSucces(BaseModel):
    detail: str = Field(examples=['Se ha actualizado la informacion del projecto'])

class ProjectDeleteSucces(BaseModel):
    detail: str = Field(examples=['Se ha eliminado el proyecto'])

class GroupCreateSucces(BaseModel):
    detail: str = Field(examples=['Se ha creado un nuevo grupo de forma exitosa'])

class GroupUpdateSucces(BaseModel):
    detail: str = Field(examples=['Se ha actualizado la informacion del grupo'])

class GroupDeleteSucces(BaseModel):
    detail: str = Field(examples=['Se ha eliminado el grupo'])

class ProjectAppendUserSucces(BaseModel):
    detail: str = Field(examples=['El usuario ha sido agregado al proyecto'])

class ProjectDeleteUserSucces(BaseModel):
    detail: str = Field(examples=['El usuario ha sido eliminado del proyecto'])

class ProjectUPdateUserSucces(BaseModel):
    detail: str = Field(examples=['Se ha cambiado los permisos del usuario en el proyecto'])

class GroupAppendUserSucces(BaseModel):
    detail: str = Field(examples=['El usuario ha sido agregado al grupo'])

class GroupDeleteUserSucces(BaseModel):
    detail: str = Field(examples=['El usuario ha sido eliminado del grupo'])

class GroupUPdateUserSucces(BaseModel):
    detail: str = Field(examples=['Se ha cambiado los permisos del usuario en el grupo'])

class NotFound(BaseModel):
    detail: str = Field(examples=[
            [
            'Group whit group_id 1 not found',
            'Project whit project_id 1 not found',
            'Chat whit project_id 1 not found',
            'User whit user_id 1 not found'
            ]
        ])
class DatabaseErrorResponse(BaseModel):
    detail: str = Field(example=["database error en {funcion}: connection timeout"])

class NotAuthorized(BaseModel):
    detail: str = Field(example=["User whit user_id 1 is Not Authorized"])