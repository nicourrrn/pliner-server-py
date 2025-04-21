from databases import Database as DatabaseCore
from datetime import datetime
import sqlite3

from pkg.models import User, Process, Step


def from_dart_datetime_to_timestamp(dart_datetime: str) -> int:
    """
    Convert a Dart datetime string to a Unix timestamp.
    The Dart datetime string is in the format 'YYYY-MM-DDTHH:MM:SS.sssZ'.
    """
    dt = datetime.strptime(dart_datetime, "%Y-%m-%dT%H:%M:%S.%f")
    return int(dt.timestamp())


def from_timestamp_to_dart_datetime(timestamp: int) -> str:
    """
    Convert a Unix timestamp to a Dart datetime string.
    The Dart datetime string is in the format 'YYYY-MM-DDTHH:MM:SS.sss'.
    """
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")


class Database:
    def __init__(self, db_name: str):
        self.connection = DatabaseCore(db_name)

    async def connect(self):
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
                assignedAt int,
                owner TEXT,
                editAt int,
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
        await self.connection.disconnect()


async def create_user(db: Database, username: str, password: str):
    query = "INSERT INTO users (username, password) VALUES (:username, :password)"
    await db.connection.execute(
        query=query, values={"username": username, "password": password}
    )


async def create_process(db: Database, process: Process, owner: str):
    query = """
        INSERT INTO processes (id, name, description, isMandatory, processType, timeNeeded, group_name, deadline, assignedAt, owner, editAt)
        VALUES (:id, :name, :description, :isMandatory, :processType, :timeNeeded, :group, :deadline, :assignedAt, :owner, :editAt)
    """
    values = process.model_dump()
    values["owner"] = owner
    values["assignedAt"] = from_dart_datetime_to_timestamp(process.assignedAt)
    values["editAt"] = from_dart_datetime_to_timestamp(process.editAt)
    del values["steps"]
    try:
        await db.connection.execute(query=query, values=values)
    except sqlite3.IntegrityError:
        query_update = """
            UPDATE processes
            SET name = :name, description = :description, isMandatory = :isMandatory, processType = :processType,
                timeNeeded = :timeNeeded, group_name = :group, deadline = :deadline, assignedAt = :assignedAt, owner = :owner, editAt = :editAt
            WHERE id = :id and editAt < :editAt 
        """
        await db.connection.execute(query=query_update, values=values)

    for step in process.steps:
        await create_step(db, step, process.id)


async def update_process(db: Database, process: Process, owner: str):
    query_update = """
        UPDATE processes
        SET name = :name, description = :description, isMandatory = :isMandatory, processType = :processType,
            timeNeeded = :timeNeeded, group_name = :group, deadline = :deadline, assignedAt = :assignedAt, owner = :owner, editAt = :editAt
        WHERE id = :id and editAt < :editAt
    """
    values = process.model_dump()
    values["owner"] = owner
    values["assignedAt"] = from_dart_datetime_to_timestamp(process.assignedAt)
    values["editAt"] = from_dart_datetime_to_timestamp(process.editAt)
    del values["steps"]
    await db.connection.execute(query=query_update, values=values)


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


async def update_step(db: Database, step: Step, process_id: str):
    values = step.model_dump() | {"process_id": process_id}
    query = """
            UPDATE steps
            SET text = :text, done = :done, isMandatory = :isMandatory, process_id = :process_id 
            WHERE id = :id
        """
    await db.connection.execute(query=query, values=values)


async def get_user(db: Database, username: str) -> User | None:
    query = "SELECT * FROM users WHERE username = :username"
    row = await db.connection.fetch_one(query=query, values={"username": username})
    if row:
        return User(username=row["username"], password=row["password"], processes=[])
    return None


async def get_process(db: Database, process_id: str) -> Process | None:
    query = "SELECT * FROM processes WHERE id = :id"
    row = await db.connection.fetch_one(query=query, values={"id": process_id})
    if row:
        steps = await get_steps(db, process_id)
        assignedAt = from_timestamp_to_dart_datetime(row["assignedAt"])
        editAt = from_timestamp_to_dart_datetime(row["editAt"])
        return Process(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            isMandatory=row["isMandatory"],
            processType=row["processType"],
            timeNeeded=row["timeNeeded"],
            group=row["group_name"],
            deadline=row["deadline"],
            assignedAt=assignedAt,
            steps=steps,
            editAt=editAt,
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
        assignedAt = from_timestamp_to_dart_datetime(row["assignedAt"])
        editAt = from_timestamp_to_dart_datetime(row["editAt"])
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
                assignedAt=assignedAt,
                steps=steps,
                editAt=editAt,
            )
        )

    print("Process getted")
    return processes


async def get_usernames(db: Database) -> list[str]:
    query = "SELECT username FROM users"
    rows = await db.connection.fetch_all(query=query)
    return [row["username"] for row in rows]


async def delete_process(db: Database, process_id: str):
    query = "DELETE from steps WHERE process_id = :process_id"
    await db.connection.execute(query=query, values={"process_id": process_id})
    query = "DELETE from processes WHERE id = :id"
    await db.connection.execute(query=query, values={"id": process_id})
    print("deleted")


async def delete_steps(db: Database, step_ids: list[str]):
    query = "DELETE from steps WHERE id IN :ids"
    await db.connection.execute(query=query, values={"ids": tuple(step_ids)})
