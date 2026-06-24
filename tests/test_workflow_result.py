import pytest

from engine.schemas import AgentState
from workflow.result import get_workflow_outcome


def make_state(status: str) -> AgentState:
    return AgentState(
        task="task",
        original_files={},
        current_files={},
        status=status,
    )


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("ready_to_apply", "approved"),
        ("dry_run_completed", "dry_run"),
        ("rejected", "rejected"),
        ("failed", "failed"),
        ("candidate_generated", "unknown"),
    ],
)
def test_get_workflow_outcome(status, expected):
    state = make_state(status)

    assert get_workflow_outcome(state) == expected


@pytest.mark.parametrize(
    ("pending_action", "expected"),
    [
        ("apply_changes", "approved"),
        ("dry_run", "dry_run"),
        ("reject", "rejected"),
        ("restore_backup", "failed"),
    ],
)
def test_get_workflow_outcome_uses_pending_action(
    pending_action,
    expected,
):
    state = AgentState(
        task="task",
        original_files={},
        current_files={},
        status="candidate_generated",
        pending_action=pending_action,
    )

    assert get_workflow_outcome(state) == expected
