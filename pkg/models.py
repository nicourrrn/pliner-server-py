from pydantic import BaseModel, Field
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
    editAt: str


class User(BaseModel):
    username: str
    password: str
    processes: list[Process] = Field(default_factory=list)
