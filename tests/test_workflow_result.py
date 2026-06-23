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