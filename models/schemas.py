from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from typing import List, Optional
from datetime import datetime as dt
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
    project_id: int = Field(examples=[1])
    description: str = Field(examples=['Actualizar los datos'])
    date_exp: dt = Field(examples=['2025-10-24'])
    state: State = Field(examples=[State.EN_PROCESO])

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

    @field_validator("date_exp")
    def date_exp_must_be_future(cls, value):
        if value <= dt.now():
            raise ValueError('La fechad expiración debe ser en el futuro.')
        return value

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
    refresh_token: str

class Access_Token(BaseModel):
    access_token: str = Field(examples=[])
    token_type: str = Field(examples=['bearer'])

class Message(BaseModel):
    content: str = Field(max_length=150, examples=['Hola a todos!'])
    user_id: int = Field(examples=[1])
    project_id: int = Field(examples=[1])
    timestamp: dt = Field(examples=['2025-10-15 09:12:12'])

class ChatMessage(BaseModel):
    chat_id: int
    project_id: int
    user_id: int 
    message: str
    timestamp: dt

class WebSocketEvent(BaseModel):
    type: str
    payload: dict

class GroupMessagePayload(BaseModel):
    content: str

class OutgoingGroupMessagePayload(BaseModel):
    id: int
    project_id: int
    sender_id: int
    content: str
    timestamp: dt

class NotificationPayload(BaseModel):
    notification_type: str # Por ejemplo: 'new_task', 'update_task'
    message: str
    related_entity_id: int | None = None # ID de la tarea, mencion, etc

class OutgoingNotificationPayload(BaseModel):
    notification_type: str # Por ejemplo: 'new_task', 'update_task'
    message: str
    related_entity_id: int | None = None # ID de la tarea, mencion, etc
    timestamp: dt

class PersonalMessagePayload(BaseModel):
    content: str
    received_user_id: int

class OutgoingPersonalMessagePayload(BaseModel):
    sender_id: int
    received_user_id: int
    content: str
    timestamp: dt