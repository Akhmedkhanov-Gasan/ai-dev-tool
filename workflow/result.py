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
    if state.pending_action == "apply_changes":
        return "approved"

    if state.pending_action == "dry_run":
        return "dry_run"

    if state.pending_action == "reject":
        return "rejected"

    if state.pending_action == "restore_backup":
        return "failed"

    if state.status == "ready_to_apply":
        return "approved"

    if state.status == "dry_run_completed":
        return "dry_run"

    if state.status == "rejected":
        return "rejected"

    if state.status == "failed":
        return "failed"

    return "unknown"
