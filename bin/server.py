from fastapi import FastAPI
from contextlib import asynccontextmanager

from pkg.router import router, user_router, process_router, deleted_process_router
from pkg.database import Database, delete_process
from pkg.middleware import PrintHttpRequestMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = Database("sqlite+aiosqlite:///database.db")
    await db.connect()
    app.state.db = db
    print("db connected")
    yield
    await db.close()
    print("Database disconnected")


app = FastAPI(lifespan=lifespan)
app.include_router(router, tags=["main"])
app.include_router(user_router, tags=["user"])
app.include_router(process_router, tags=["process"])
app.include_router(deleted_process_router, tags=["deleted"])

app.add_middleware(PrintHttpRequestMiddleware)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
