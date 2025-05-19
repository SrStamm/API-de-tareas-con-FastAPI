from fastapi import HTTPException, status

class NotAuthorized(HTTPException):
    def __init__(self, user_id):
        self.user_id = user_id
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'User with user_id {user_id} is Not Authorized'
        )

class InvalidToken(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'Token Not Authorized'
        )

class UserNotFoundInLogin(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'User not found'
        )

class LoginError(HTTPException):
    def __init__(self, user_id):
        self.user_id = user_id
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Password incorrect'
        )

class UserWithUsernameExist(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=f'Ya existe un usuario con este Username'
        )

class UserWithEmailExist(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=f'Ya existe un usuario con este Email'
        )

class GroupNotFoundError(HTTPException):
    def __init__(self, group_id):
        self.group_id = group_id
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Group with group_id {group_id} not found'
        )

class ProjectNotFoundError(HTTPException):
    def __init__(self, project_id):
        self.project_id = project_id
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Project with project_id {project_id} not found'
        )

class ChatNotFoundError(HTTPException):
    def __init__(self, project_id):
        self.project_id = project_id
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Chat with project_id {project_id} not found'
        )

class UserNotFoundError(HTTPException):
    def __init__(self, user_id):
        self.user_id = user_id
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'User with user_id {user_id} not found'
        )

class CommentNotFoundError(HTTPException):
    def __init__(self, task_id):
        self.task_id = task_id
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Comments not found in task_id {task_id}'
        )

class UserNotAuthorizedInCommentError(HTTPException):
    def __init__(self, user_id, comment_id):
        self.user_id = user_id
        self.comment_id = comment_id
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'User with user_id {user_id} is not authorized to edit this comment {comment_id}'
        )

class UserInProjectError(HTTPException):
    def __init__(self, user_id, project_id):
        self.user_id = user_id
        self.project_id = project_id
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'User with user_id {user_id} is in project with project_id {project_id}'
        )

class UserNotInProjectError(HTTPException):
    def __init__(self, user_id, project_id):
        self.user_id = user_id
        self.project_id = project_id
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'User with user_id {user_id} is not in project with project_id {project_id}'
        )

class UserInGroupError(HTTPException):
    def __init__(self, user_id, group_id):
        self.user_id = user_id
        self.group_id = group_id
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'User with user_id {user_id} is in Group with group_id {group_id}'
        )

class UserNotInGroupError(HTTPException):
    def __init__(self, user_id, group_id):
        self.user_id = user_id
        self.group_id = group_id
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'User with user_id {user_id} is not in Group with group_id {group_id}'
        )

class UsersNotFoundInProjectError(HTTPException):
    def __init__(self, project_id):
        self.project_id = project_id
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Users is not found in Project with project_id {project_id}'
        )

class TaskNotFound(HTTPException):
    def __init__(self, task_id, project_id):
        self.task_id = task_id
        self.project_id = project_id
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Task with task_id {task_id} is not in Project with project_id {project_id}'
        )

class TaskErrorNotFound(HTTPException):
    def __init__(self, task_id):
        self.task_id = task_id
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Task with task_id {task_id} not found'
        )

class TaskIsAssignedError(HTTPException):
    def __init__(self, task_id, user_id):
        self.task_id = task_id
        self.user_id = user_id
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Task with task_id {task_id} is assigned to User with user_id {user_id}'
        )

class TaskIsNotAssignedError(HTTPException):
    def __init__(self, task_id, user_id):
        self.task_id = task_id
        self.user_id = user_id
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Task with task_id {task_id} is NOT assigned to User with user_id {user_id}'
        )

class DatabaseError(HTTPException):
    def __init__(self, error, func: str):
        self.error = error
        self.func = func
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'database error en {func}: {str(error)}'
        )

class SessionNotFound(HTTPException):
    def __init__(self, user_id):
        self.user_id = user_id
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Session not found for user {user_id}'
        )