from fastapi.routing import APIRouter
from fastapi import Request

from pkg.database import (
    create_user,
    create_process,
    get_user,
    get_process,
    get_steps,
    get_all_user_processes,
)

from pkg.models import User, Process


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
