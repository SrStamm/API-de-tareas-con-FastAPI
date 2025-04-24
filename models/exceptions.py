from fastapi import HTTPException, status

class NotAuthorized(HTTPException):
    def __init__(self, user_id):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'User whit user_id {user_id} is Not Authorized'
        )

class GroupNotFoundError(HTTPException):
    def __init__(self, group_id):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Group whit group_id {group_id} not found'
        )

class ProjectNotFoundError(HTTPException):
    def __init__(self, project_id):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Project whit project_id {project_id} not found'
        )

class ChatNotFoundError(HTTPException):
    def __init__(self, project_id):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Chat whit project_id {project_id} not found'
        )

class UserNotFoundError(HTTPException):
    def __init__(self, user_id):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'User whit user_id {user_id} not found'
        )

class UserInProjectError(HTTPException):
    def __init__(self, user_id, project_id):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'User whit user_id {user_id} is in project with project_id {project_id}'
        )

class UserNotInProjectError(HTTPException):
    def __init__(self, user_id, project_id):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'User whit user_id {user_id} is not in project with project_id {project_id}'
        )

class UserInGroupError(HTTPException):
    def __init__(self, user_id, group_id):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'User whit user_id {user_id} is in Group with group_id {group_id}'
        )

class UserNotInGroupError(HTTPException):
    def __init__(self, user_id, group_id):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'User whit user_id {user_id} is not in Group with group_id {group_id}'
        )

class DatabaseError(HTTPException):
    def __init__(self, error, func: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'database error en {func}: {str(error)}'
        )