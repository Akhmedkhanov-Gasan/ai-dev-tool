from typing import Literal

from engine.schemas import AgentState

WorkflowOutcome = Literal[
    "approved",
    "dry_run",
    "rejected",
    "failed",
    "unknown",
]


def get_workflow_outcome(state: AgentState) -> WorkflowOutcome:
    if state.status == "approved":
        return "approved"

    if state.status == "dry_run_completed":
        return "dry_run"

    if state.status == "rejected":
        return "rejected"

    if state.status == "failed":
        return "failed"

    return "unknown"