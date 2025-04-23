from pydantic import BaseModel, Field
from typing import Any
import uuid


class SqliteModel(BaseModel):
    def model_dump(self, *args, **kwargs) -> dict:
        original = super().model_dump(*args, **kwargs)
        new = self._convert_to_int(original)
        return new

    @classmethod
    def _convert_to_int(cls, data):
        if isinstance(data, dict):
            return {k: cls._convert_to_int(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls._convert_to_int(i) for i in data]
        elif isinstance(data, bool):
            return int(data)
        return data

    @classmethod
    def model_validate(cls, obj: Any, **kwargs):
        clean_data = cls._convert_to_bools(obj)
        return super().model_validate(clean_data, **kwargs)

    @classmethod
    def _convert_to_bools(cls, data):
        if isinstance(data, dict):
            return {
                k: cls._convert_to_bools(int(v) if isinstance(v, bool) else v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [cls._convert_to_bools(i) for i in data]
        return data


class Step(SqliteModel):
    id: str
    text: str
    done: bool
    isMandatory: bool


class Process(SqliteModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = Field(default="")
    isMandatory: bool = Field(default=False)
    processType: str
    timeNeeded: int
    groupName: str
    deadline: str
    assignedAt: str
    steps: list[Step] = Field(default_factory=list)
    editAt: str


class User(BaseModel):
    username: str
    password: str
    processes: list[Process] = Field(default_factory=list)
