from pydantic import BaseModel, Field

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