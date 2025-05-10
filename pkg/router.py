from fastapi.routing import APIRouter
from fastapi import HTTPException, Request

from pkg.database import (
    create_user,
    create_process,
    delete_process,
    delete_steps,
    get_deleted_processes,
    get_edit_at_by_user,
    get_processes_by_user,
    get_steps_by_process,
    get_user,
    get_process,
    get_users,
    is_deleted_process,
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


@user_router.get("/")
async def get_users_endpoint(req: Request) -> list[str]:
    db = req.app.state.db
    users = await get_users(db)
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
        user.processes = await get_processes_by_user(db, user.username)
        return user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


process_router = APIRouter(prefix="/processes", tags=["process"])


@process_router.get("/")
async def get_processes_endpoint(owner: str, req: Request) -> list[Process]:
    db = req.app.state.db
    try:
        processes = await get_processes_by_user(db, owner)
        for process in processes:
            process.steps = await get_steps_by_process(db, process.id)
        return processes
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@process_router.get("/last_edites")
async def get_last_updates_endpoint(owner: str, req: Request) -> list[EditAtProcess]:
    db = req.app.state.db
    try:
        return [
            EditAtProcess(
                id=process.id,
                editAt=process.editAt,
            )
            for process in await get_edit_at_by_user(db, owner)
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@process_router.get("/{process_id}")
async def get_process_endpoint(process_id: str, req: Request) -> Process:
    db = req.app.state.db
    try:
        process = await get_process(db, process_id)
        if not process:
            raise HTTPException(status_code=404, detail="Process not found")
        process.steps = await get_steps_by_process(db, process_id)
        return process
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@process_router.post("/")
async def create_process_endpoint(items: list[Process], owner: str, req: Request):
    db = req.app.state.db
    for process in items:
        try:
            await create_process(db, process, owner)
        except Exception:
            ...


@process_router.put("/")
async def update_process_endpoint(processes: list[Process], owner: str, req: Request):
    db = req.app.state.db
    for process in processes:
        try:
            await update_process(db, process, owner)
            for step in process.steps:
                await update_step(db, step)
        except Exception as e:
            ...


@process_router.delete("/")
async def delete_process_endpoint(items: list[str], req: Request):
    db = req.app.state.db
    for process_id in items:
        try:
            await delete_process(db, process_id)
        except Exception:
            ...


@process_router.get("/{process_id}/steps")
async def get_step_list_endpoint(process_id: str, req: Request):
    db = req.app.state.db
    try:
        steps = await get_steps_by_process(db, process_id)
        if steps:
            return steps
        raise HTTPException(status_code=404, detail="Steps not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@process_router.put("/{process_id}/steps")
async def update_step_list_endpoint(steps: list[Step], req: Request):
    db = req.app.state.db
    for step in steps:
        try:
            await update_step(db, step)
        except Exception:
            ...


# @process_router.delete("/steps")
# async def delete_step_list_endpoint(step_ids: list[str], req: Request):
#     db = req.app.state.db
#     try:
#         await delete_steps(db, step_ids)
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))


deleted_process_router = APIRouter(prefix="/processes/deleted", tags=["deleted"])


@deleted_process_router.get("/")
async def get_deleted_processes_endpoint(req: Request) -> list[str]:
    db = req.app.state.db
    try:
        return await get_deleted_processes(db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@deleted_process_router.post("/")
async def delete_processes(items: list[str], req: Request):
    db = req.app.state.db
    for process_id in items:
        try:
            await delete_process(db, process_id)
        except Exception as e:
            ...


@deleted_process_router.get("/{process_id}")
async def is_deleted_process_endpoint(
    process_id: str, req: Request
) -> IsDeletedProcess:
    db = req.app.state.db
    try:
        return IsDeletedProcess(
            id=process_id,
            isDeleted=await is_deleted_process(db, process_id),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ping")
async def ping_endpoint():
    return None, 200
