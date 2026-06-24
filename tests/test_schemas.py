import pytest

from engine.schemas import AgentState, ValidationResult


def test_agent_state_stores_initial_agent_data():
    state = AgentState(
        task="Add /status endpoint",
        original_files={"demo_app/main.py": "old app"},
        current_files={"demo_app/main.py": "new app"},
        candidate_files={"demo_app/main.py": "candidate app"},
        retrieved_context="context",
        last_validation_result=ValidationResult(ok=True, phase="passed"),
        iteration=1,
        status="running",
    )

    assert state.task == "Add /status endpoint"
    assert state.original_files["demo_app/main.py"] == "old app"
    assert state.current_files["demo_app/main.py"] == "new app"
    assert state.retrieved_context == "context"
    assert state.iteration == 1
    assert state.status == "running"
    assert state.candidate_files["demo_app/main.py"] == "candidate app"
    assert state.last_validation_result is not None
    assert state.last_validation_result.ok is True
    assert state.last_validation_result.phase == "passed"


def test_agent_state_errors_are_not_shared_between_instances():
    first_state = AgentState(
        task="first",
        original_files={},
        current_files={},
    )
    second_state = AgentState(
        task="second",
        original_files={},
        current_files={},
    )

    first_state.errors.append("first error")

    assert first_state.errors == ["first error"]
    assert second_state.errors == []


def test_validation_result_stores_validation_data():
    result = ValidationResult(
        ok=False,
        phase="ruff",
        message="Ruff error",
    )

    assert result.ok is False
    assert result.phase == "ruff"
    assert result.message == "Ruff error"


def test_validation_result_uses_empty_message_by_default():
    result = ValidationResult(ok=True, phase="passed")

    assert result.message == ""


def test_validation_result_rejects_empty_phase():
    with pytest.raises(ValueError, match="phase must not be empty"):
        ValidationResult(ok=False, phase=" ")


def test_agent_state_workflow_fields_use_defaults():
    state = AgentState(
        task="task",
        original_files={},
        current_files={},
    )

    assert state.candidate_files == {}
    assert state.last_validation_result is None
    assert state.review_decision is None


@pytest.mark.parametrize(
    "decision",
    ["approve", "reject", "dry_run"],
)
def test_agent_state_stores_review_decision(decision):
    state = AgentState(
        task="task",
        original_files={},
        current_files={},
        review_decision=decision,
    )

    assert state.review_decision == decision


def test_agent_state_rejects_unknown_review_decision():
    with pytest.raises(ValueError, match="review_decision"):
        AgentState(
            task="task",
            original_files={},
            current_files={},
            review_decision="maybe",
        )


def test_agent_state_pending_action_is_empty_by_default():
    state = AgentState(
        task="task",
        original_files={},
        current_files={},
    )

    assert state.pending_action is None


def test_agent_state_stores_pending_action():
    state = AgentState(
        task="task",
        original_files={},
        current_files={},
        pending_action="apply_changes",
    )

    assert state.pending_action == "apply_changes"
