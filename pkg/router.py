from fastapi.responses import FileResponse
from fastapi.routing import APIRouter
from fastapi import HTTPException, Request
import pprint

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

from pkg.models import (
    EditAtProcess,
    IsDeletedProcess,
    User,
    Process,
    Step,
)


router = APIRouter()
user_router = APIRouter(prefix="/users", tags=["user"])
process_router = APIRouter(prefix="/processes", tags=["process"])
deleted_process_router = APIRouter(prefix="/processes/deleted", tags=["deleted"])


@user_router.get("/")
async def get_all_users_endpoint(req: Request) -> list[str]:
    db = req.app.state.db
    users = await db.get_usernames()
    return users


@user_router.post("/")
async def create_user_endpoint(user: User, req: Request):
    db = req.app.state.db
    try:
        await create_user(db, user.username, user.password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@user_router.get("/{username}")
async def get_user_endpoint(username: str, req: Request) -> User:
    db = req.app.state.db
    try:
        user = await get_user(db, username)
        user.processes = await get_all_user_processes(db, user)
        return user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@process_router.get("/{process_id}")
async def get_process_endpoint(
    process_id: str, with_steps: bool, req: Request
) -> Process:
    db = req.app.state.db
    try:
        process = await get_process(db, process_id)
        if not process:
            raise HTTPException(status_code=404, detail="Process not found")
        if with_steps:
            process.steps = await get_steps(db, process_id)
            return process
        return process
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@process_router.post("/")
async def create_process_endpoint(process: Process, owner: str, req: Request):
    db = req.app.state.db
    try:
        await create_process(db, process, owner)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@process_router.put("/")
async def update_process_endpoint(process: Process, owner: str, req: Request):
    db = req.app.state.db
    try:
        await update_process(db, process, owner)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@process_router.delete("/{process_id}")
async def delete_process_endpoint(process_id: str, req: Request):
    db = req.app.state.db
    try:
        await delete_process(db, process_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@deleted_process_router.get("/")
async def get_deleted_processes_endpoint(req: Request) -> list[str]:
    db = req.app.state.db
    try:
        return await get_deleted_processes(db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@deleted_process_router.post("/")
async def restore_process_endpoint(items: list[str], req: Request):
    db = req.app.state.db
    try:
        for process_id in items:
            await delete_process(db, process_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@deleted_process_router.get("/{process_id}")
async def is_process_deleted_endpoint(
    process_id: str, req: Request
) -> IsDeletedProcess:
    db = req.app.state.db
    try:
        return IsDeletedProcess(
            id=process_id,
            isDeleted=await is_process_deleted(db, process_id),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# @router.get("/processes/user/{username}")
# async def get_user_processes_endpoint(username: str, req: Request) -> list[Process]:
#     db = req.app.state.db
#     user = await get_user(db, username)
#     if user:
#         processes = await get_all_user_processes(db, user)
#         for process in processes:
#             pprint.pprint(process.model_dump())
#         return processes
#     raise Exception("User not found")


@process_router.get("/last_updates")
async def get_last_updates_endpoint(req: Request) -> list[EditAtProcess]:
    db = req.app.state.db
    try:
        return [
            EditAtProcess(
                id=process["id"],
                editAt=process["editAt"],
            )
            for process in await db.get_all_processes()
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@process_router.get("/{process_id}/steps")
async def get_steps_endpoint(process_id: str, req: Request):
    db = req.app.state.db
    try:
        steps = await get_steps(db, process_id)
        if steps:
            return steps
        raise HTTPException(status_code=404, detail="Steps not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@process_router.put("/{process_id}/steps")
async def update_steps_endpoint(process_id: str, steps: list[Step], req: Request):
    db = req.app.state.db
    try:
        for step in steps:
            await update_step(db, step, process_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@process_router.delete("/steps")
async def delete_steps_endpoint(step_ids: list[str], req: Request):
    db = req.app.state.db
    try:
        await delete_steps(db, step_ids)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ping")
async def ping_endpoint():
    return None, 200
