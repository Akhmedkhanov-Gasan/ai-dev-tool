from pydantic import BaseModel, ConfigDict, Field, field_validator


class GeneratedFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    content: str

    @field_validator("path")
    @classmethod
    def path_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("path must not be empty")

        return value

    @field_validator("content")
    @classmethod
    def content_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be empty")

        return value


class GeneratedFiles(BaseModel):
    model_config = ConfigDict(extra="forbid")

    files: list[GeneratedFile]


class AgentState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: str
    original_files: dict[str, str]
    current_files: dict[str, str]
    retrieved_context: str = ""
    errors: list[str] = Field(default_factory=list)
    iteration: int = 0
    status: str = "started"
    