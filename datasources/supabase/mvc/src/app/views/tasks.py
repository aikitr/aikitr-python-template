from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)

    @field_validator("title", mode="before")
    @classmethod
    def trim_title(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    completed: bool
