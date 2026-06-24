from langgraph.graph import END

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


def test_generation_failure_routes_to_retry():
    state = make_state(status="generation_failed")

    assert graph.route_after_generation(state) == "prepare_retry_or_fail"


def test_successful_generation_routes_to_guard():
    state = make_state(status="candidate_generated")

    assert graph.route_after_generation(state) == "route_guard"


def test_guard_failure_routes_to_retry():
    state = make_state(status="route_protection_failed")

    assert graph.route_after_guard(state) == "prepare_retry_or_fail"


def test_successful_guard_routes_to_baseline_validation():
    state = make_state(status="route_protection_passed")

    assert graph.route_after_guard(state) == "baseline_validation"


def test_baseline_failure_routes_to_retry():
    state = make_state(status="baseline_validation_failed")

    assert graph.route_after_baseline(state) == "prepare_retry_or_fail"


def test_successful_baseline_routes_to_candidate_validation():
    state = make_state(status="baseline_validation_passed")

    assert graph.route_after_baseline(state) == "candidate_validation"


def test_successful_candidate_validation_routes_to_human_review():
    state = make_state(status="candidate_validation_passed")

    assert graph.route_after_candidate(state) == "request_human_review"


def test_failed_candidate_validation_routes_to_retry():
    state = make_state(status="candidate_validation_failed")

    assert graph.route_after_candidate(state) == "prepare_retry_or_fail"


def test_retry_status_routes_to_generation():
    state = make_state(status="retrying")

    assert graph.route_after_retry(state) == "generate_candidate"


def test_failed_status_ends_workflow():
    state = make_state(status="failed")

    assert graph.route_after_retry(state) == END


def test_workflow_completes_successful_path(monkeypatch):
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

    result = graph.run_agent_workflow(make_state())

    assert result.status == "human_review_required"
    assert result.iteration == 1
    assert result.candidate_files == candidate_files


def test_workflow_stops_after_max_generation_failures(monkeypatch):
    calls = []

    def fail_generation(state):
        calls.append(state.iteration)
        return {
            "iteration": state.iteration + 1,
            "status": "generation_failed",
            "final_error_phase": "code generation",
            "errors": [*state.errors, "generation failed"],
        }

    monkeypatch.setattr(graph, "generate_candidate", fail_generation)

    result = graph.run_agent_workflow(
        make_state(max_iterations=2)
    )

    assert result.status == "failed"
    assert result.pending_action == "restore_backup"
    assert result.iteration == 2
    assert result.final_error_phase == "code generation"
    assert result.errors == [
        "generation failed",
        "generation failed",
    ]
    assert len(calls) == 2
