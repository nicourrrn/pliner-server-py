from fastapi.responses import FileResponse
from fastapi.routing import APIRouter
from fastapi import Request

from pkg.database import (
    create_user,
    create_process,
    delete_process,
    delete_steps,
    get_deleted_processes,
    get_user,
    get_process,
    get_steps,
    get_all_user_processes,
    is_process_deleted,
    update_process,
    update_step,
)

from pkg.models import User, Process, Step


router = APIRouter()


@router.get("/users/{username}")
async def get_user_endpoint(username: str, req: Request):
    db = req.app.state.db
    user = await get_user(db, username)
    if user:
        user.processes = await get_all_user_processes(db, user)
        return user
    return {"message": "User not found"}


@router.post("/users/")
async def create_user_endpoint(user: User, req: Request):
    db = req.app.state.db
    await create_user(db, user.username, user.password)
    return {"message": "User created successfully"}


@router.get("/users/")
async def get_all_users_endpoint(req: Request):
    db = req.app.state.db
    users = await db.get_usernames()
    return users


@router.post("/processes/")
async def create_process_endpoint(process: Process, owner: str, req: Request):
    db = req.app.state.db
    await create_process(db, process, owner)
    return {"message": "Process created successfully"}


@router.put("/processes/")
async def update_process_endpoint(process: Process, owner: str, req: Request):
    db = req.app.state.db
    await update_process(db, process, owner)
    return {"message": "Process updated successfully"}


@router.get("/processes/deleted")
async def get_deleted_processes_endpoint(req: Request):
    db = req.app.state.db
    deleted_processes = await get_deleted_processes(db)
    return deleted_processes


@router.get("/processes/deleted/{process_id}")
async def is_process_deleted_endpoint(process_id: str, req: Request):
    db = req.app.state.db
    is_deleted = await is_process_deleted(db, process_id)
    return {"is_deleted": is_deleted}


@router.get("/processes/{process_id}")
async def get_process_endpoint(process_id: str, with_steps: bool, req: Request):
    db = req.app.state.db
    process = await get_process(db, process_id)
    if not process:
        return {"message": "Process not found"}
    if with_steps:
        process.steps = await get_steps(db, process_id)
        return process
    return process


@router.get("/steps/{process_id}")
async def get_steps_endpoint(process_id: str, req: Request):
    db = req.app.state.db
    steps = await get_steps(db, process_id)
    if steps:
        return steps
    return {"message": "Steps not found"}


@router.get("/processes/user/{username}")
async def get_user_processes_endpoint(username: str, req: Request):
    db = req.app.state.db
    user = await get_user(db, username)
    if user:
        processes = await get_all_user_processes(db, user)
        return processes
    return {"message": "User not found"}


@router.delete("/processes/{process_id}")
async def delete_process_endpoint(process_id: str, req: Request):
    db = req.app.state.db
    await delete_process(db, process_id)
    return {"message": "Process deleted successfully"}


@router.get("/processes/last_updates")
async def get_last_updates_endpoint(req: Request):
    db = req.app.state.db
    processes = await db.get_all_processes()
    last_updates = [
        {
            "id": process.id,
            "last_update": process.editAt,
        }
        for process in processes
    ]
    return last_updates


@router.delete("/steps")
async def delete_steps_endpoint(step_ids: list[str], req: Request):
    db = req.app.state.db
    await delete_steps(db, step_ids)
    return {"message": "Steps deleted successfully"}


@router.put("/processes/{process_id}/steps")
async def update_steps_endpoint(process_id: str, steps: list[Step], req: Request):
    db = req.app.state.db
    for step in steps:
        await update_step(db, step, process_id)
    return {"message": "Steps updated successfully"}


@router.get("/application/{platform}")
async def get_application_version_endpoint(platform: str, req: Request):
    return {"last_version": 2, "platform": platform}


@router.get("/application/{platform}/app")
async def get_application_endpoint(platform: str, req: Request) -> FileResponse:
    if platform == "android":
        return FileResponse("static/app.apk")
    elif platform == "windows":
        return FileResponse("static/app.exe")
    elif platform == "linux":
        return FileResponse("static/app.tar.gz")
    else:
        raise Exception(
            "Platform not supported. Supported platforms are: android, windows, linux"
        )


@router.get("/ping")
async def ping_endpoint(req: Request):
    return {"message": "pong"}
