from pydantic import BaseModel, Field
from fastapi import FastAPI
from databases import Database as DatabaseCore
from typing import Optional
from fastapi import Request
import sqlite3

import uuid


class Step(BaseModel):
    id: str
    text: str
    done: bool
    isMandatory: bool


class Process(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = Field(default="")
    isMandatory: bool = Field(default=False)
    processType: str
    timeNeeded: int
    group: str
    deadline: str
    assignedAt: str
    steps: list[Step] = Field(default_factory=list)


class User(BaseModel):
    username: str
    password: str
    processes: list[Process] = Field(default_factory=list)


class Database:
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.connection: Optional[DatabaseCore] = None

    async def connect(self):
        self.connection = DatabaseCore(self.db_name)
        await self.connection.connect()
        await self.create_tables()

    async def create_tables(self):
        await self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT
            )
        """
        )
        await self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS processes (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                isMandatory BOOLEAN,
                processType TEXT,
                timeNeeded INTEGER,
                group_name TEXT,
                deadline TEXT,
                assignedAt TEXT,
                owner TEXT,
                FOREIGN KEY (owner) REFERENCES users (username)
            )
        """
        )
        await self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS steps (
                id TEXT PRIMARY KEY,
                text TEXT,
                done BOOLEAN,
                isMandatory BOOLEAN,
                process_id TEXT,
                FOREIGN KEY (process_id) REFERENCES processes (id)
            )
        """
        )

    async def close(self):
        if self.connection:
            await self.connection.disconnect()


async def create_user(db: Database, username: str, password: str):
    query = "INSERT INTO users (username, password) VALUES (:username, :password)"
    await db.connection.execute(
        query=query, values={"username": username, "password": password}
    )


async def create_process(db: Database, process: Process, owner: str):
    query = """
        INSERT INTO processes (id, name, description, isMandatory, processType, timeNeeded, group_name, deadline, assignedAt, owner)
        VALUES (:id, :name, :description, :isMandatory, :processType, :timeNeeded, :group, :deadline, :assignedAt, :owner)
    """
    values = process.model_dump()
    values["owner"] = owner
    del values["steps"]
    try:
        await db.connection.execute(query=query, values=values)
    except sqlite3.IntegrityError:
        query_update = """
            UPDATE processes
            SET name = :name, description = :description, isMandatory = :isMandatory, processType = :processType,
                timeNeeded = :timeNeeded, group_name = :group, deadline = :deadline, assignedAt = :assignedAt, owner = :owner
            WHERE id = :id
        """
        await db.connection.execute(query=query_update, values=values)

    for step in process.steps:
        await create_step(db, step, process.id)


async def create_step(db: Database, step: Step, process_id: str):
    query = """
        INSERT INTO steps (id, text, done, isMandatory, process_id)
        VALUES (:id, :text, :done, :isMandatory, :process_id)
    """
    values = step.model_dump()
    values["process_id"] = process_id
    try:
        await db.connection.execute(query=query, values=values)
    except sqlite3.IntegrityError:
        query_update = """
            UPDATE steps
            SET text = :text, done = :done, isMandatory = :isMandatory, process_id = :process_id 
            WHERE id = :id 
        """
        await db.connection.execute(query=query_update, values=values)


async def get_user(db: Database, username: str) -> Optional[User]:
    query = "SELECT * FROM users WHERE username = :username"
    row = await db.connection.fetch_one(query=query, values={"username": username})
    if row:
        return User(username=row["username"], password=row["password"], processes=[])
    return None


async def get_process(db: Database, process_id: str) -> Optional[Process]:
    query = "SELECT * FROM processes WHERE id = :id"
    row = await db.connection.fetch_one(query=query, values={"id": process_id})
    if row:
        steps = await get_steps(db, process_id)
        return Process(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            isMandatory=row["isMandatory"],
            processType=row["processType"],
            timeNeeded=row["timeNeeded"],
            group=row["group_name"],
            deadline=row["deadline"],
            assignedAt=row["assignedAt"],
            steps=steps,
        )
    return None


async def get_steps(db: Database, process_id: str) -> list[Step]:
    query = "SELECT * FROM steps WHERE process_id = :process_id"
    rows = await db.connection.fetch_all(query=query, values={"process_id": process_id})
    return [
        Step(
            id=row["id"],
            text=row["text"],
            done=row["done"],
            isMandatory=row["isMandatory"],
        )
        for row in rows
    ]


async def get_all_user_processes(db: Database, user: User) -> list[Process]:
    query = "SELECT * FROM processes WHERE owner = :owner"
    rows = await db.connection.fetch_all(query=query, values={"owner": user.username})
    processes = []
    for row in rows:
        steps = await get_steps(db, row["id"])
        processes.append(
            Process(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                isMandatory=row["isMandatory"],
                processType=row["processType"],
                timeNeeded=row["timeNeeded"],
                group=row["group_name"],
                deadline=row["deadline"],
                assignedAt=row["assignedAt"],
                steps=steps,
            )
        )
    return processes


from contextlib import asynccontextmanager


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


@app.post("/users/")
async def create_user_endpoint(user: User, req: Request):
    db = req.app.state.db
    await create_user(db, user.username, user.password)
    return {"message": "User created successfully"}


@app.post("/processes/")
async def create_process_endpoint(process: Process, owner: str, req: Request):
    db = req.app.state.db
    await create_process(db, process, owner)
    return {"message": "Process created successfully"}


@app.get("/users/{username}")
async def get_user_endpoint(username: str, req: Request):
    db = req.app.state.db
    user = await get_user(db, username)
    if user:
        user.processes = await get_all_user_processes(db, user)
        return user
    return {"message": "User not found"}


@app.get("/processes/{process_id}")
async def get_process_endpoint(process_id: str, req: Request):
    db = req.app.state.db
    process = await get_process(db, process_id)
    if process:
        process.steps = await get_steps(db, process_id)
        return process
    return {"message": "Process not found"}


@app.get("/steps/{process_id}")
async def get_steps_endpoint(process_id: str, req: Request):
    db = req.app.state.db
    steps = await get_steps(db, process_id)
    if steps:
        return steps
    return {"message": "Steps not found"}


@app.get("/processes/user/{username}")
async def get_user_processes_endpoint(username: str, req: Request):
    db = req.app.state.db
    user = await get_user(db, username)
    if user:
        processes = await get_all_user_processes(db, user)
        return processes
    return {"message": "User not found"}


def main():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
