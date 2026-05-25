from engine.schemas import AgentState


def test_agent_state_stores_initial_agent_data():
    state = AgentState(
        task="Add /status endpoint",
        original_files={"demo_app/main.py": "old app"},
        current_files={"demo_app/main.py": "new app"},
        retrieved_context="context",
        iteration=1,
        status="running",
    )

    assert state.task == "Add /status endpoint"
    assert state.original_files["demo_app/main.py"] == "old app"
    assert state.current_files["demo_app/main.py"] == "new app"
    assert state.retrieved_context == "context"
    assert state.iteration == 1
    assert state.status == "running"


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