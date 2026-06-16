from engine.project_files import APP_FILE_PATH, TEST_FILE_PATH
from engine.schemas import AgentState, ValidationResult
from workflow import nodes


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
        "candidate_files": {
            APP_FILE_PATH: "candidate app",
            TEST_FILE_PATH: "candidate tests",
        },
        "agent_rules": "rules",
        "retrieved_context": "context",
        "max_iterations": 3,
    }
    data.update(updates)
    return AgentState(**data)


def test_generate_candidate_stores_generated_files(monkeypatch):
    generated_files = {
        APP_FILE_PATH: "generated app",
        TEST_FILE_PATH: "generated tests",
    }

    monkeypatch.setattr(
        nodes,
        "generate_code",
        lambda *args: generated_files,
    )

    result = nodes.generate_candidate(make_state())

    assert result["iteration"] == 1
    assert result["status"] == "candidate_generated"
    assert result["candidate_files"] == generated_files


def test_generate_candidate_records_generation_error(monkeypatch):
    def fail_generation(*args):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(nodes, "generate_code", fail_generation)

    result = nodes.generate_candidate(make_state(errors=["old error"]))

    assert result["iteration"] == 1
    assert result["status"] == "generation_failed"
    assert result["final_error_phase"] == "code generation"
    assert result["errors"] == [
        "old error",
        "Code generation failed:\nmodel unavailable",
    ]


def test_route_guard_passes_when_routes_are_preserved(monkeypatch):
    monkeypatch.setattr(
        nodes,
        "find_removed_get_routes",
        lambda old_code, new_code: set(),
    )

    result = nodes.route_guard(make_state())

    assert result == {"status": "route_protection_passed"}


def test_route_guard_records_removed_routes(monkeypatch):
    monkeypatch.setattr(
        nodes,
        "find_removed_get_routes",
        lambda old_code, new_code: {"/health"},
    )

    result = nodes.route_guard(make_state())

    assert result["status"] == "route_protection_failed"
    assert result["final_error_phase"] == "route protection"
    assert "/health" in result["errors"][-1]


def test_baseline_validation_uses_original_tests(monkeypatch):
    captured = {}

    def fake_check_code(files, original_files):
        captured["files"] = files
        captured["original_files"] = original_files
        return ValidationResult(ok=True, phase="passed")

    monkeypatch.setattr(nodes, "check_code", fake_check_code)

    state = make_state()
    result = nodes.baseline_validation(state)

    assert captured["files"] == {
        APP_FILE_PATH: "candidate app",
        TEST_FILE_PATH: "original tests",
    }
    assert captured["original_files"] == state.original_files
    assert result["status"] == "baseline_validation_passed"
    assert result["last_validation_result"].ok is True


def test_baseline_validation_records_failure(monkeypatch):
    monkeypatch.setattr(
        nodes,
        "check_code",
        lambda files, original_files: ValidationResult(
            ok=False,
            phase="pytest",
            message="original test failed",
        ),
    )

    result = nodes.baseline_validation(make_state())

    assert result["status"] == "baseline_validation_failed"
    assert result["final_error_phase"] == "baseline validation: pytest"
    assert "original test failed" in result["errors"][-1]


def test_candidate_validation_passes(monkeypatch):
    monkeypatch.setattr(
        nodes,
        "check_code",
        lambda files, original_files: ValidationResult(
            ok=True,
            phase="passed",
        ),
    )

    result = nodes.candidate_validation(make_state())

    assert result["status"] == "candidate_validation_passed"
    assert result["last_validation_result"].ok is True


def test_candidate_validation_prepares_failed_candidate_for_retry(monkeypatch):
    monkeypatch.setattr(
        nodes,
        "check_code",
        lambda files, original_files: ValidationResult(
            ok=False,
            phase="ruff",
            message="missing import",
        ),
    )

    state = make_state(errors=["old error"])
    result = nodes.candidate_validation(state)

    assert result["status"] == "candidate_validation_failed"
    assert result["final_error_phase"] == "candidate validation: ruff"
    assert result["errors"] == ["old error", "missing import"]
    assert result["current_files"] == state.candidate_files


def test_prepare_retry_when_iterations_remain():
    result = nodes.prepare_retry_or_fail(
        make_state(iteration=2, max_iterations=3)
    )

    assert result == {"status": "retrying"}


def test_prepare_failure_when_iteration_limit_is_reached():
    result = nodes.prepare_retry_or_fail(
        make_state(iteration=3, max_iterations=3)
    )

    assert result == {"status": "failed"}


def test_request_human_review_marks_state_as_waiting_for_human():
    result = nodes.request_human_review(make_state())

    assert result == {"status": "human_review_required"}
