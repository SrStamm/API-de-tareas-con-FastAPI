from pydantic import (
    BaseModel,
    Field,
    EmailStr,
    ConfigDict,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)
from typing import List, Optional
from datetime import datetime as dt, timezone
from .db_models import State, Group_Role, Project_Permission, TypeOfLabel, TaskLabelLink

# User


class CreateUser(BaseModel):
    username: str = Field(examples=["User64"])
    email: EmailStr = Field(examples=["User@gmail.com"])
    password: str = Field(examples=["0ga0"])


class UpdateUser(BaseModel):
    username: str | None = Field(default=None, examples=["user64"])
    email: EmailStr | None = Field(default=None, examples=["newuser@email.com"])
    password: str | None = Field(default=None, examples=["asd5a51564"])


class UpdateRoleUser(BaseModel):
    role: Group_Role | None = Field(
        default=None, examples=[Group_Role.EDITOR, Group_Role.MEMBER]
    )


class UpdatePermissionUser(BaseModel):
    permission: Project_Permission | None = Field(
        default=None, examples=[Project_Permission.READ, Project_Permission.WRITE]
    )


class ReadUser(BaseModel):
    user_id: int = Field(examples=[1])
    username: str = Field(examples=["user5892"])

    model_config = ConfigDict(from_attributes=True)


class ReadRoleUser(BaseModel):
    user_id: int = Field(examples=[1])
    group_id: int
    role: Group_Role

    model_config = ConfigDict(from_attributes=True)


class ReadGroupUser(BaseModel):
    user_id: int = Field(examples=[1])
    username: str = Field(examples=["User64"])
    role: Group_Role = Field(examples=["User@gmail.com"])

    model_config = ConfigDict(from_attributes=True)


class ReadProjectUser(BaseModel):
    user_id: int = Field(examples=[1])
    username: str = Field(examples=["User64"])
    permission: Project_Permission = Field(examples=[Project_Permission.WRITE])

    model_config = ConfigDict(from_attributes=True)


class ReadPermissionUser(BaseModel):
    user_id: int
    project_id: int
    permission: Project_Permission


# Task


class CreateTask(BaseModel):
    title: str = Field(examples=["Actualizar la API"])
    description: str | None = Field(
        default=None,
        examples=[
            "Debido a varios cambios, se debe actualizar en las siguientes partes..."
        ],
    )
    date_exp: Optional[dt] = Field(default=None, examples=["2025-10-28"])
    assigned_user_id: int | None = None
    label: List[TypeOfLabel] | None = None

    @field_validator("date_exp")
    def date_exp_must_be_future(cls, value):
        if value and value <= dt.now():
            raise ValueError("La fechad expiración debe ser en el futuro.")
        return value


class ReadLabel(BaseModel):
    label: TypeOfLabel

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def __pydantic_init__(cls, obj: TaskLabelLink):
        if not isinstance(obj, TaskLabelLink):
            super().__pydantic_init__(obj)
        else:
            return cls(label=obj.label)


class ReadTask(BaseModel):
    task_id: int
    project_id: int
    title: str = Field(examples=["TaskAPI"])
    description: str | None
    assigned_user: ReadUser | None
    date_exp: Optional[dt]
    state: State
    task_label_links: List[ReadLabel] | None = None

    model_config = ConfigDict(from_attributes=True)


class ReadTaskInProject(BaseModel):
    task_id: int = Field(examples=[1])
    title: str = Field(examples=["TaskAPI"])
    description: str | None = Field(default=None, examples=[])
    date_exp: Optional[dt]
    state: State = Field(examples=[])
    assigned_user: ReadUser | None
    task_label_links: Optional[List[ReadLabel]] | None = None

    model_config = ConfigDict(from_attributes=True)


class UpdateTask(BaseModel):
    title: str | None = Field(default=None, examples=["Error en Front"])

    description: str | None = Field(
        default=None,
    )
    date_exp: dt | None = Field(default=None, examples=["2025-12-20"])
    state: State | None = Field(default=None, examples=[State.CANCELADO])
    assigned_user_id: Optional[int] = Field(default=None)
    remove_assigned_user_id: bool = False

    remove_label: Optional[List[TypeOfLabel]] | None = Field(
        default=None, examples=[TypeOfLabel.HIGH_PRIORITY, TypeOfLabel.BACKEND]
    )
    append_label: Optional[List[TypeOfLabel]] | None = Field(
        default=None, examples=[TypeOfLabel.BUG, TypeOfLabel.FRONTEND]
    )


# Comment


class CreateComment(BaseModel):
    content: str = Field(max_length=300)


class ReadComment(BaseModel):
    comment_id: int
    task_id: int
    user_id: int
    username: str
    content: str
    created_at: dt
    update_at: dt
    is_deleted: bool


class UpdateComment(BaseModel):
    content: str = Field(max_length=300)
    update_at: dt = Field(default_factory=lambda: dt.now(timezone.utc))
    is_deleted: Optional[bool] = Field(default=None)


# Group


class CreateGroup(BaseModel):
    name: str = Field(examples=["Google"])
    description: str | None = Field(default=None, examples=["Somos un navegador Web"])


class ReadGroup(BaseModel):
    group_id: int = Field(examples=[1])
    name: str = Field(examples=["Facebook"])
    description: str | None = Field(default=None, examples=["Red Social"])
    users: List[ReadUser] = Field(
        examples=[
            [
                {"username": "user89", "user_id": 1},
                {"username": "user_falso", "user_id": 5},
            ]
        ]
    )

    model_config = ConfigDict(from_attributes=True)


class ReadBasicDataGroup(BaseModel):
    group_id: int = Field(examples=[1])
    name: str = Field(examples=["Amazon"])
    users: List[ReadUser] = Field(
        examples=[
            [
                {"username": "user89", "user_id": 1},
                {"username": "user_falso", "user_id": 5},
            ]
        ]
    )


class UpdateGroup(BaseModel):
    name: str | None = Field(default=None, examples=["AWS"])
    description: str | None = Field(default=None, examples=["Servicio en la Nube"])


# Project


class CreateProject(BaseModel):
    title: str = Field(examples=["Crear un nuevo Microservicio"])
    description: str | None = Field(
        default=None, examples=["Subida y bajada de archivos"]
    )


class ReadProject(BaseModel):
    project_id: int = Field(examples=[1])
    group_id: int = Field(examples=[1])
    title: str = Field(examples=["TaskAPI"])
    description: str | None = Field(
        examples=["API que maneja tareas asignadas a usuarios"]
    )
    users: List[ReadUser] = Field(
        examples=[
            [
                {"username": "user89", "user_id": 1},
                {"username": "user_falso", "user_id": 5},
            ]
        ]
    )

    model_config = ConfigDict(from_attributes=True)


class ReadBasicProject(BaseModel):
    project_id: int = Field(examples=[1])
    group_id: int = Field(examples=[1])
    title: str = Field(examples=["TaskAPI"])
    description: str | None = Field(
        examples=["API que maneja tareas asignadas a usuarios"]
    )

    model_config = ConfigDict(from_attributes=True)


class UpdateProject(BaseModel):
    title: str | None = Field(default=None, examples=["ChatRealTime"])
    description: str | None = Field(
        default=None, examples=["Chat en tiempo real que maneje millones de conexiones"]
    )


# Token
class Token(BaseModel):
    access_token: str = Field(examples=[])
    token_type: str = Field(examples=["bearer"])
    refresh_token: str


class Access_Token(BaseModel):
    access_token: str = Field(examples=[])
    token_type: str = Field(examples=["bearer"])


class RefreshTokenRequest(BaseModel):
    refresh: str


# Mensaje y WebSocket


class Message(BaseModel):
    content: str = Field(max_length=150, examples=["Hola a todos!"])
    user_id: int = Field(examples=[1])
    project_id: int = Field(examples=[1])
    timestamp: dt = Field(examples=["2025-10-15 09:12:12"])


class ChatMessage(BaseModel):
    chat_id: int
    project_id: int
    user_id: int
    username: str
    message: str
    timestamp: dt

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def get_username_from_obj(cls, data):
        if data.user or data["user"]:
            return {
                "chat_id": data.chat_id,
                "project_id": data.project_id,
                "user_id": data.user_id,
                "username": data.user.username,
                "message": data.message,
                "timestamp": data.timestamp,
            }

        raise ValueError


class WebSocketEvent(BaseModel):
    type: str
    payload: dict


class GroupMessagePayload(BaseModel):
    content: str
    project_id: int


class OutgoingGroupMessagePayload(BaseModel):
    id: int
    project_id: int
    sender_id: int
    content: str
    timestamp: dt


class NotificationPayload(BaseModel):
    notification_type: str  # Por ejemplo: 'new_task', 'update_task'
    message: str
    related_entity_id: int | None = None  # ID de la tarea, mencion, etc


class OutgoingNotificationPayload(BaseModel):
    notification_type: str  # Por ejemplo: 'new_task', 'update_task'
    message: str
    related_entity_id: int | None = None  # ID de la tarea, mencion, etc
    timestamp: dt = Field(default_factory=lambda: dt.now())


class PersonalMessagePayload(BaseModel):
    content: str
    received_user_id: int


class OutgoingPersonalMessagePayload(BaseModel):
    sender_id: int
    received_user_id: int
    content: str
    timestamp: dt
