from fastapi import FastAPI
from contextlib import asynccontextmanager

from pkg.router import router
from pkg.database import Database


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
app.include_router(router, prefix="", tags=["main"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
