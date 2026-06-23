from engine.project_files import APP_FILE_PATH, TEST_FILE_PATH
from engine.schemas import AgentState, ValidationResult
from workflow import graph


def make_state(**updates) -> AgentState:
    data = {
        "task": "Add endpoint",
        "original_files": {
            APP_FILE_PATH: "original app",
            TEST_FILE_PATH: "original tests",
        },
        "current_files": {
            APP_FILE_PATH: "current app",
            TEST_FILE_PATH: "current tests",
        },
        "max_iterations": 3,
    }
    data.update(updates)
    return AgentState(**data)


def test_run_agent_workflow_calls_on_update_for_successful_path(monkeypatch):
    candidate_files = {
        APP_FILE_PATH: "generated app",
        TEST_FILE_PATH: "generated tests",
    }

    def fake_generate(state):
        return {
            "iteration": state.iteration + 1,
            "status": "candidate_generated",
            "candidate_files": candidate_files,
        }

    monkeypatch.setattr(graph, "generate_candidate", fake_generate)
    monkeypatch.setattr(
        graph,
        "route_guard",
        lambda state: {"status": "route_protection_passed"},
    )
    monkeypatch.setattr(
        graph,
        "baseline_validation",
        lambda state: {
            "status": "baseline_validation_passed",
            "last_validation_result": ValidationResult(
                ok=True,
                phase="passed",
            ),
        },
    )
    monkeypatch.setattr(
        graph,
        "candidate_validation",
        lambda state: {
            "status": "candidate_validation_passed",
            "last_validation_result": ValidationResult(
                ok=True,
                phase="passed",
            ),
        },
    )

    updates = []
    reviewed_states = []

    result = graph.run_agent_workflow(
        make_state(),
        on_update=lambda node_name, update: updates.append(
            (node_name, update["status"])
        ),
        on_review=lambda state: (
                reviewed_states.append(state) or "approve"
        ),
    )

    assert updates == [
        ("generate_candidate", "candidate_generated"),
        ("route_guard", "route_protection_passed"),
        ("baseline_validation", "baseline_validation_passed"),
        ("candidate_validation", "candidate_validation_passed"),
        ("request_human_review", "human_review_required"),
        ("request_human_review", "approved"),
        ("finalize_review", "ready_to_apply"),
    ]
    assert result.status == "ready_to_apply"
    assert result.review_decision == "approve"
    assert len(reviewed_states) == 1
    assert reviewed_states[0].status == "human_review_required"
    assert reviewed_states[0].candidate_files == candidate_files


def test_run_agent_workflow_streams_retry_path(monkeypatch):
    candidate_files = {
        APP_FILE_PATH: "generated app",
        TEST_FILE_PATH: "generated tests",
    }

    validation_attempts = []

    def fake_generate(state):
        return {
            "iteration": state.iteration + 1,
            "status": "candidate_generated",
            "candidate_files": candidate_files,
        }

    def fake_candidate_validation(state):
        validation_attempts.append(state.iteration)

        if len(validation_attempts) == 1:
            return {
                "status": "candidate_validation_failed",
                "last_validation_result": ValidationResult(
                    ok=False,
                    phase="pytest",
                    message="test failed",
                ),
                "final_error_phase": "candidate validation: pytest",
                "errors": [*state.errors, "test failed"],
                "current_files": state.candidate_files,
            }

        return {
            "status": "candidate_validation_passed",
            "last_validation_result": ValidationResult(
                ok=True,
                phase="passed",
            ),
        }

    monkeypatch.setattr(graph, "generate_candidate", fake_generate)
    monkeypatch.setattr(
        graph,
        "route_guard",
        lambda state: {"status": "route_protection_passed"},
    )
    monkeypatch.setattr(
        graph,
        "baseline_validation",
        lambda state: {
            "status": "baseline_validation_passed",
            "last_validation_result": ValidationResult(
                ok=True,
                phase="passed",
            ),
        },
    )
    monkeypatch.setattr(graph, "candidate_validation", fake_candidate_validation)

    updates = []

    result = graph.run_agent_workflow(
        make_state(max_iterations=2),
        on_update=lambda node_name, update: updates.append(
            (node_name, update["status"])
        ),
    )

    assert updates == [
        ("generate_candidate", "candidate_generated"),
        ("route_guard", "route_protection_passed"),
        ("baseline_validation", "baseline_validation_passed"),
        ("candidate_validation", "candidate_validation_failed"),
        ("prepare_retry_or_fail", "retrying"),
        ("generate_candidate", "candidate_generated"),
        ("route_guard", "route_protection_passed"),
        ("baseline_validation", "baseline_validation_passed"),
        ("candidate_validation", "candidate_validation_passed"),
        ("request_human_review", "human_review_required"),
    ]
    assert result.status == "human_review_required"
    assert result.iteration == 2
    assert result.errors == ["test failed"]


def test_run_agent_workflow_returns_failed_state_after_streaming_retries(
    monkeypatch,
):
    def fail_generation(state):
        return {
            "iteration": state.iteration + 1,
            "status": "generation_failed",
            "final_error_phase": "code generation",
            "errors": [*state.errors, "generation failed"],
        }

    monkeypatch.setattr(graph, "generate_candidate", fail_generation)

    updates = []

    result = graph.run_agent_workflow(
        make_state(max_iterations=2),
        on_update=lambda node_name, update: updates.append(
            (node_name, update["status"])
        ),
    )

    assert updates == [
        ("generate_candidate", "generation_failed"),
        ("prepare_retry_or_fail", "retrying"),
        ("generate_candidate", "generation_failed"),
        ("prepare_retry_or_fail", "failed"),
    ]
    assert result.status == "failed"
    assert result.iteration == 2
    assert result.final_error_phase == "code generation"
    assert result.errors == [
        "generation failed",
        "generation failed",
    ]
