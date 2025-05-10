from databases import Database as DatabaseCore
from datetime import datetime
import sqlite3

from pkg.models import DatabaseException, EditAtProcess, User, Process, Step


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
            CREATE TABLE IF NOT EXISTS deletedProcesses (
                id TEXT PRIMARY KEY
            )
        """
        )
        await self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS processes (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                isMandatory INT,
                processType TEXT,
                timeNeeded INTEGER,
                groupName TEXT,
                deadline TEXT,
                assignedAt INT,
                owner TEXT,
                editAt INT,
                FOREIGN KEY (owner) REFERENCES users (username)
            )
        """
        )
        await self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS steps (
                id TEXT PRIMARY KEY,
                text TEXT,
                done INT,
                isMandatory INT,
                processId TEXT,
                FOREIGN KEY (processId) REFERENCES processes (id)
            )
        """
        )

    async def close(self):
        await self.connection.disconnect()


async def get_users(db: Database) -> list[str]:
    query = "SELECT username FROM users"
    rows = await db.connection.fetch_all(query=query)
    return [row["username"] for row in rows]


async def create_user(db: Database, username: str, password: str):
    query = "INSERT INTO users (username, password) VALUES (:username, :password)"
    await db.connection.execute(
        query=query, values={"username": username, "password": password}
    )


async def get_user(db: Database, username: str) -> User:
    query = "SELECT * FROM users WHERE username = :username"
    row = await db.connection.fetch_one(query=query, values={"username": username})
    if row:
        return User(username=row["username"], password=row["password"], processes=[])
    raise DatabaseException("User not found")


async def get_process(db: Database, process_id: str) -> Process:
    query = "SELECT * FROM processes WHERE id = :id"
    row = await db.connection.fetch_one(query=query, values={"id": process_id})
    if row:
        assignedAt = from_timestamp_to_dart_datetime(row["assignedAt"])
        editAt = from_timestamp_to_dart_datetime(row["editAt"])
        return Process(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            isMandatory=row["isMandatory"],
            processType=row["processType"],
            timeNeeded=row["timeNeeded"],
            groupName=row["groupName"],
            deadline=row["deadline"],
            assignedAt=assignedAt,
            steps=[],
            editAt=editAt,
        )
    raise DatabaseException("Process not found")


async def get_processes_by_user(db: Database, owner: str) -> list[Process]:
    query = "SELECT * FROM processes WHERE owner = :owner"
    rows = await db.connection.fetch_all(query=query, values={"owner": owner})
    processes = []
    for row in rows:
        steps = await get_steps_by_process(db, row["id"])
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
                groupName=row["groupName"],
                deadline=row["deadline"],
                assignedAt=assignedAt,
                steps=steps,
                editAt=editAt,
            )
        )
    return processes


async def get_edit_at_by_user(db: Database, owner: str) -> list[EditAtProcess]:
    query = "SELECT id, editAt FROM processes WHERE owner = :owner"
    rows = await db.connection.fetch_all(query=query, values={"owner": owner})
    return [
        EditAtProcess(
            id=row["id"],
            editAt=from_timestamp_to_dart_datetime(row["editAt"]),
        )
        for row in rows
    ]


async def get_steps_by_process(db: Database, process_id: str) -> list[Step]:
    query = "SELECT * FROM steps WHERE processId = :processId"
    rows = await db.connection.fetch_all(query=query, values={"processId": process_id})
    return [
        Step(
            id=row["id"],
            text=row["text"],
            done=row["done"],
            isMandatory=row["isMandatory"],
        )
        for row in rows
    ]


async def create_process(db: Database, process: Process, owner: str):
    if await is_deleted_process(db, process.id):
        raise DatabaseException("Process already deleted")

    query = """
        INSERT INTO processes (id, name, description, isMandatory, processType, timeNeeded, groupName, deadline, assignedAt, owner, editAt)
        VALUES (:id, :name, :description, :isMandatory, :processType, :timeNeeded, :groupName, :deadline, :assignedAt, :owner, :editAt)
    """
    values = process.model_dump(exclude={"steps"}) | {"owner": owner}
    values["assignedAt"] = from_dart_datetime_to_timestamp(process.assignedAt)
    values["editAt"] = from_dart_datetime_to_timestamp(process.editAt)
    try:
        await db.connection.execute(query=query, values=values)
    except sqlite3.IntegrityError:
        raise DatabaseException("Process already exists")

    for step in process.steps:
        await create_step(db, step, process.id)


async def create_step(db: Database, step: Step, process_id: str):
    query = """
        INSERT INTO steps (id, text, done, isMandatory, processId)
        VALUES (:id, :text, :done, :isMandatory, :processId)
    """
    values = step.model_dump() | {"processId": process_id}
    try:
        await db.connection.execute(query=query, values=values)
    except sqlite3.IntegrityError:
        raise DatabaseException("Step already exists")


async def update_process(db: Database, process: Process, owner: str):
    query_update = """
        UPDATE processes
        SET name = :name, description = :description, isMandatory = :isMandatory, processType = :processType,
            timeNeeded = :timeNeeded, groupName = :groupName, deadline = :deadline, assignedAt = :assignedAt,
            owner = :owner, editAt = :editAt
        WHERE id = :id and editAt < :editAt
    """
    values = process.model_dump(exclude={"steps"}) | {"onwer": owner}
    values["assignedAt"] = from_dart_datetime_to_timestamp(process.assignedAt)
    values["editAt"] = from_dart_datetime_to_timestamp(process.editAt)
    await db.connection.execute(query=query_update, values=values)


async def update_step(db: Database, step: Step):
    values = step.model_dump()
    query = """
            UPDATE steps
            SET text = :text, done = :done, isMandatory = :isMandatory 
            WHERE id = :id
        """
    await db.connection.execute(query=query, values=values)


async def delete_process(db: Database, process_id: str):
    query = "DELETE from steps WHERE processId = :processId"
    await db.connection.execute(query=query, values={"processId": process_id})
    query = "DELETE from processes WHERE id = :id"
    await db.connection.execute(query=query, values={"id": process_id})
    try:
        query = "INSERT INTO deletedProcesses (id) VALUES (:id)"
        await db.connection.execute(query=query, values={"id": process_id})
    except sqlite3.IntegrityError:
        raise DatabaseException("Process already deleted")


async def get_deleted_processes(db: Database) -> list[str]:
    query = "SELECT id FROM deletedProcesses"
    rows = await db.connection.fetch_all(query=query)
    return [row["id"] for row in rows]


async def is_deleted_process(db: Database, process_id: str) -> bool:
    query = "SELECT id FROM deletedProcesses WHERE id = :id"
    row = await db.connection.fetch_one(query=query, values={"id": process_id})
    return row is not None


async def delete_steps(db: Database, step_ids: list[str]):
    query = "DELETE from steps WHERE id IN :ids"
    await db.connection.execute(query=query, values={"ids": tuple(step_ids)})
