from fastapi import APIRouter, Depends, Request, Query
from models import schemas, responses
from models.db_models import User, TypeOfLabel, State
from typing import List
from core.permission import require_permission
from core.logger import logger
from core.limiter import limiter
from dependency.auth_dependencies import get_current_user
from dependency.task_dependencies import get_task_service, TaskService

router = APIRouter(prefix="/task", tags=["Task"])


@router.get(
    "",
    summary="Get all tasks assigned to the user",
    description=""" Obtain all of assigned tasks this user.
                    'skip' receives an "int" that skips the result obtained.
                    'limit' receives an "int" that limits the result obtained.
                    'labels' receives a list with labels to filter the task.
                    'state' receives a list with states to filter the task.""",
    responses={
        200: {"description": "Tasks obtained", "model": schemas.ReadTask},
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("30/minute")
async def get_task(
    request: Request,
    limit: int = 10,
    skip: int = 0,
    labels: List[TypeOfLabel] = Query(default=None),
    state: List[State] = Query(default=None),
    user: User = Depends(get_current_user),
    task_serv: TaskService = Depends(get_task_service),
) -> List[schemas.ReadTask]:
    return await task_serv.get_all_task_for_user(
        user.user_id, limit, skip, labels, state
    )


@router.get(
    "/{project_id}",
    summary="Get all task to the project",
    description=""" Obtain all assigned proyect tasks.
                        'skip' receives an "int" that skips the result obtained.
                        'limit' receives an "int" that limits the result obtained.
                        'labels' receives a list with labels to filter the task.
                        'state' receives a list with states to filter the task.""",
    responses={
        200: {
            "description": "Tasks from project obtained",
            "model": schemas.ReadTaskInProject,
        },
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("15/minute")
async def get_task_in_project(
    request: Request,
    project_id: int,
    limit: int = 10,
    skip: int = 0,
    labels: List[TypeOfLabel] = Query(default=None),
    state: List[State] = Query(default=None),
    _: User = Depends(get_current_user),
    task_serv: TaskService = Depends(get_task_service),
) -> List[schemas.ReadTaskInProject]:
    return await task_serv.get_all_task_for_project(
        project_id, limit, skip, labels, state
    )


@router.post(
    "/{project_id}",
    summary="Create a new task",
    description="Create a new task to the project. Need a description, expiration date, users_ids to assign the task, and a label to task",
    responses={
        201: {"description": "Task created", "model": responses.TaskCreateSucces},
        404: {"description": "Data not found", "model": responses.DataNotFound},
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("10/minute")
async def create_task(
    request: Request,
    new_task: schemas.CreateTask,
    project_id: int,
    auth_data: dict = Depends(require_permission(permissions=["admin"])),
    task_serv: TaskService = Depends(get_task_service),
):
    return await task_serv.create(new_task, project_id)


@router.patch(
    "/{project_id}/{task_id}",
    summary="",
    description="Update a specific task from the proyect",
    responses={
        200: {"description": "Task updated", "model": responses.TaskUpdateSucces},
        400: {"description": "Error in request", "model": responses.ErrorInRequest},
        401: {"description": "Unauthorized", "model": responses.NotAuthorized},
        404: {"description": "Data not foun", "model": responses.DataNotFound},
        500: {
            "description": "internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("10/minute")
async def update_task(
    request: Request,
    task_id: int,
    project_id: int,
    update_task: schemas.UpdateTask,
    auth_data: dict = Depends(require_permission(permissions=["admin", "write"])),
    task_serv: TaskService = Depends(get_task_service),
):
    actual_permission = auth_data["permission"]

    return await task_serv.update_task(
        task_id, project_id, update_task, actual_permission
    )


@router.delete(
    "/{project_id}/{task_id}",
    summary="Delete the task",
    description="Removes a specific task from a project. Need a task_id",
    responses={
        200: {"description": "Task removed", "model": responses.TaskDeleteSucces},
        400: {"description": "Error in request", "model": responses.ErrorInRequest},
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
async def delete_task(
    task_id: int,
    project_id: int,
    _: dict = Depends(require_permission(permissions=["admin"])),
    task_serv: TaskService = Depends(get_task_service),
):
    return await task_serv.delete(task_id, project_id)
