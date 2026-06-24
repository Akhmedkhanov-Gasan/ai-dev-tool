from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal


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


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    phase: str
    message: str = ""

    @field_validator("phase")
    @classmethod
    def phase_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("phase must not be empty")

        return value

class AgentState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: str
    original_files: dict[str, str]
    current_files: dict[str, str]
    candidate_files: dict[str, str] = Field(default_factory=dict)
    retrieved_context: str = ""
    errors: list[str] = Field(default_factory=list)
    last_validation_result: ValidationResult | None = None
    iteration: int = 0
    status: str = "started"
    agent_rules: str = ""
    final_error_phase: str = ""
    max_iterations: int = 3
    review_decision: Literal["approve", "reject", "dry_run"] | None = None
    pending_action: Literal[
                        "apply_changes",
                        "dry_run",
                        "reject",
                        "restore_backup",
                    ] | None = None
