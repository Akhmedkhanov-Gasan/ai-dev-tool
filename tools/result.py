from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    name: str
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must not be empty")

        return value
