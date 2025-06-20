from fastapi import APIRouter, Depends, Request
from models import schemas, responses
from models.db_models import User
from typing import List
from core.logger import logger
from core.limiter import limiter
from dependency.user_dependencies import get_user_service, UserService
from dependency.auth_dependencies import get_current_user

router = APIRouter(prefix="/user", tags=["User"])


@router.get(
    "",
    summary="Get all users",
    description=""" Obtain all of users.
                    'skip' receives an "int" that skips the result obtained.
                    'limit' receives an "int" that limits the result obtained.""",
    responses={
        200: {"description": "Users obtained", "model": schemas.ReadUser},
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("20/minute")
async def get_users(
    request: Request,
    limit: int = 10,
    skip: int = 0,
    user_serv: UserService = Depends(get_user_service),
) -> List[schemas.ReadUser]:
    return await user_serv.get_all_users(limit, skip)


@router.post(
    "",
    summary="Create a new user",
    description="""Create a new user. Need a username, an email and a password""",
    responses={
        201: {"description": "User created", "model": responses.UserCreateSucces},
        406: {"description": "Data conflict", "model": responses.UserConflictError},
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("5/minute")
async def create_user(
    request: Request,
    new_user: schemas.CreateUser,
    user_serv: UserService = Depends(get_user_service),
):
    return await user_serv.create_user(new_user)


@router.get(
    "/me",
    summary="Get data from user",
    description="Obtain current user information",
    responses={
        200: {"description": "Obtained current user", "model": schemas.ReadUser},
        500: {
            "description": "Internal errro",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("20/minute")
def get_user_me(
    request: Request, user: User = Depends(get_current_user)
) -> schemas.ReadUser:
    try:
        return user
    except Exception as e:
        logger.error(f"[get_user_me] Unknown Error | Error: {str(e)}")
        raise


@router.patch(
    "/me",
    summary="Update the user",
    description="Update current user",
    responses={
        200: {
            "description": "Current user updated",
            "model": responses.UserUpdateSucces,
        },
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("5/minute")
async def update_user_me(
    request: Request,
    updated_user: schemas.UpdateUser,
    user: User = Depends(get_current_user),
    user_serv: UserService = Depends(get_user_service),
):
    return await user_serv.update_user(user, updated_user)


@router.delete(
    "/me",
    summary="Delete the user",
    description="Delete current user",
    responses={
        200: {
            "description": "Current user deleted",
            "model": responses.UserDeleteSucces,
        },
        500: {
            "description": "Internal error",
            "model": responses.DatabaseErrorResponse,
        },
    },
)
@limiter.limit("5/minute")
async def delete_user_me(
    request: Request,
    user: User = Depends(get_current_user),
    user_serv: UserService = Depends(get_user_service),
):
    return await user_serv.delete_user(user)
