from engine.generation import generate_code
from engine.project_files import APP_FILE_PATH, TEST_FILE_PATH
from engine.routes import find_removed_get_routes
from engine.schemas import AgentState
from engine.validation import check_code

from langgraph.types import interrupt


def generate_candidate(state: AgentState) -> dict:
    iteration = state.iteration + 1
    error_context = "\n\n".join(state.errors)

    try:
        candidate_files = generate_code(
            state.task,
            state.current_files,
            error_context,
            state.retrieved_context,
            state.agent_rules,
        )
    except Exception as e:
        error_message = f"Code generation failed:\n{e}"
        return {
            "iteration": iteration,
            "status": "generation_failed",
            "final_error_phase": "code generation",
            "errors": [*state.errors, error_message],
        }

    return {
        "iteration": iteration,
        "status": "candidate_generated",
        "candidate_files": candidate_files,
    }


def route_guard(state: AgentState) -> dict:
    removed_routes = find_removed_get_routes(
        state.current_files[APP_FILE_PATH],
        state.candidate_files[APP_FILE_PATH],
    )

    if removed_routes:
        error_message = (
            "Generated code removed existing routes, which is not allowed "
            f"unless the task explicitly asks for it: {sorted(removed_routes)}"
        )
        return {
            "status": "route_protection_failed",
            "final_error_phase": "route protection",
            "errors": [*state.errors, error_message],
        }

    return {"status": "route_protection_passed"}


def baseline_validation(state: AgentState) -> dict:
    baseline_files = {
        APP_FILE_PATH: state.candidate_files[APP_FILE_PATH],
        TEST_FILE_PATH: state.original_files[TEST_FILE_PATH],
    }

    result = check_code(baseline_files, state.original_files)

    if not result.ok:
        error_message = (
            "Baseline validation failed. Generated app code does not pass the original tests. "
            "Do not change existing behavior unless the task explicitly asks for it.\n"
            f"{result.message}"
        )
        return {
            "status": "baseline_validation_failed",
            "last_validation_result": result,
            "final_error_phase": f"baseline validation: {result.phase}",
            "errors": [*state.errors, error_message],
        }

    return {
        "status": "baseline_validation_passed",
        "last_validation_result": result,
    }


def candidate_validation(state: AgentState) -> dict:
    result = check_code(state.candidate_files, state.original_files)

    if not result.ok:
        return {
            "status": "candidate_validation_failed",
            "last_validation_result": result,
            "final_error_phase": f"candidate validation: {result.phase}",
            "errors": [*state.errors, result.message],
            "current_files": state.candidate_files,
        }

    return {
        "status": "candidate_validation_passed",
        "last_validation_result": result,
    }


def prepare_retry_or_fail(state: AgentState) -> dict:
    if state.iteration >= state.max_iterations:
        return {"status": "failed"}

    return {"status": "retrying"}


def request_human_review(state: AgentState) -> dict:
    decision = interrupt(
        {
            "status": "human_review_required",
            "iteration": state.iteration,
        }
    )

    statuses = {
        "approve": "approved",
        "reject": "rejected",
        "dry_run": "dry_run_completed",
    }

    if decision not in statuses:
        raise ValueError(f"Unknown review decision: {decision}")

    return {
        "review_decision": decision,
        "status": statuses[decision],
    }
