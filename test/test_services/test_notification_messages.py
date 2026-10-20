import json

import pytest

from models.schemas import CreateTask, UpdateTask
from services.task_services import TaskService


def _build_service(mocker):
    task_repo = mocker.Mock()
    user_ser = mocker.Mock()
    proj_ser = mocker.Mock()
    service = TaskService(task_repo, user_ser, proj_ser)
    return service, task_repo, user_ser, proj_ser


def _captured_message(send_to_user_mock, call_index=-1):
    raw = send_to_user_mock.call_args_list[call_index].kwargs["message"]
    return json.loads(raw)["payload"]["message"]


def _captured_event(send_to_user_mock, call_index=-1):
    raw = send_to_user_mock.call_args_list[call_index].kwargs["message"]
    return json.loads(raw)


@pytest.mark.asyncio
async def test_create_assigned_notification_is_human_readable(mocker):
    service, task_repo, user_ser, proj_ser = _build_service(mocker)
    send = mocker.patch(
        "services.task_services.manager.send_to_user", new_callable=mocker.AsyncMock
    )

    new_task = mocker.Mock()
    new_task.task_id = 9
    new_task.title = "Fix login"
    task_repo.create.return_value = new_task
    proj_ser.get_project_title_or_none.return_value = "Tasks API"

    payload = CreateTask(title="Fix login", assigned_user_id=2)

    await service.create(
        payload, project_id=3, actor_user_id=1, actor_username="mirko"
    )

    assert _captured_message(send) == (
        "Fuiste asignado a la tarea «Fix login» en el proyecto «Tasks API» por mirko."
    )
    assert _captured_event(send)["payload"]["related_entity_id"] == 9


@pytest.mark.asyncio
async def test_create_self_assignment_sends_no_notification(mocker):
    service, task_repo, user_ser, proj_ser = _build_service(mocker)
    send = mocker.patch(
        "services.task_services.manager.send_to_user", new_callable=mocker.AsyncMock
    )

    new_task = mocker.Mock()
    new_task.task_id = 9
    new_task.title = "Fix login"
    task_repo.create.return_value = new_task

    payload = CreateTask(title="Fix login", assigned_user_id=1)

    await service.create(payload, project_id=3, actor_user_id=1, actor_username="mirko")

    send.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_falls_back_to_id_message_when_title_missing(mocker):
    service, task_repo, user_ser, proj_ser = _build_service(mocker)
    send = mocker.patch(
        "services.task_services.manager.send_to_user", new_callable=mocker.AsyncMock
    )

    new_task = mocker.Mock()
    new_task.task_id = 9
    new_task.title = "Fix login"
    task_repo.create.return_value = new_task
    proj_ser.get_project_title_or_none.return_value = None

    payload = CreateTask(title="Fix login", assigned_user_id=2)

    await service.create(payload, project_id=3, actor_user_id=1, actor_username="mirko")

    assert _captured_message(send) == (
        "You were assigned to the task 9 in the project 3"
    )


@pytest.mark.asyncio
async def test_assigned_notification_omits_actor_when_unavailable(mocker):
    service, task_repo, user_ser, proj_ser = _build_service(mocker)
    send = mocker.patch(
        "services.task_services.manager.send_to_user", new_callable=mocker.AsyncMock
    )

    new_task = mocker.Mock()
    new_task.task_id = 9
    new_task.title = "Fix login"
    task_repo.create.return_value = new_task
    proj_ser.get_project_title_or_none.return_value = "Tasks API"

    payload = CreateTask(title="Fix login", assigned_user_id=2)

    await service.create(payload, project_id=3, actor_user_id=1, actor_username=None)

    assert _captured_message(send) == (
        "Fuiste asignado a la tarea «Fix login» en el proyecto «Tasks API»."
    )


@pytest.mark.asyncio
async def test_update_reassignment_notification_is_human_readable(mocker):
    service, task_repo, user_ser, proj_ser = _build_service(mocker)
    send = mocker.patch(
        "services.task_services.manager.send_to_user", new_callable=mocker.AsyncMock
    )

    task = mocker.Mock()
    task.title = "Fix login"
    task_repo.get_task_by_id.return_value = task
    proj_ser.get_project_title_or_none.return_value = "Tasks API"
    user_ser.get_user_or_404.return_value = mocker.Mock(username="mirko")

    payload = UpdateTask(assigned_user_id=2)

    await service.update_task(
        task_id=9, project_id=3, update_task=payload, permission="admin", user_id=1
    )

    assert _captured_message(send) == (
        "Fuiste asignado a la tarea «Fix login» en el proyecto «Tasks API» por mirko."
    )
    assert _captured_event(send)["payload"]["related_entity_id"] == 9


@pytest.mark.asyncio
async def test_update_self_assignment_sends_no_notification(mocker):
    service, task_repo, user_ser, proj_ser = _build_service(mocker)
    send = mocker.patch(
        "services.task_services.manager.send_to_user", new_callable=mocker.AsyncMock
    )

    task = mocker.Mock()
    task.title = "Fix login"
    task_repo.get_task_by_id.return_value = task

    payload = UpdateTask(assigned_user_id=1)

    await service.update_task(
        task_id=9, project_id=3, update_task=payload, permission="admin", user_id=1
    )

    send.assert_not_awaited()
