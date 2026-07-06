import difflib
import os

from workflow.reviews import (
    clear_review_state,
    list_review_states,
    load_review_state,
)

DEFAULT_PENDING_REVIEW_WARNING_LIMIT = 5


def show_diff(path: str, old_code: str, new_code: str):
    diff = difflib.unified_diff(
        old_code.splitlines(),
        new_code.splitlines(),
        fromfile=path,
        tofile=f"{path} updated",
        lineterm="",
    )

    print(f"\n--- DIFF: {path} ---")
    print("\n".join(diff))


def show_project_diff(old_files: dict[str, str], new_files: dict[str, str]):
    for path, old_code in old_files.items():
        show_diff(path, old_code, new_files[path])


def get_pending_review_warning_limit() -> int:
    raw_limit = os.getenv("AI_AGENT_PENDING_REVIEW_WARNING_LIMIT")

    if raw_limit is None:
        return DEFAULT_PENDING_REVIEW_WARNING_LIMIT

    try:
        limit = int(raw_limit)
    except ValueError as e:
        raise RuntimeError(
            "AI_AGENT_PENDING_REVIEW_WARNING_LIMIT must be an integer."
        ) from e

    if limit < 0:
        raise RuntimeError(
            "AI_AGENT_PENDING_REVIEW_WARNING_LIMIT must be 0 or greater."
        )

    return limit


def show_pending_reviews():
    reviews = list_review_states()

    if not reviews:
        print("No pending reviews")
        return

    print("Pending reviews:")

    for thread_id, state in reviews:
        print(
            f"{thread_id} | iteration={state.iteration} "
            f"| status={state.status} | task={state.task}"
        )


def show_review_summary():
    reviews = list_review_states()
    warning_limit = get_pending_review_warning_limit()

    print(f"Pending reviews: {len(reviews)}")

    if len(reviews) > warning_limit:
        print(
            "WARNING: pending review count is above limit: "
            f"{warning_limit}"
        )

    if not reviews:
        return

    statuses: dict[str, int] = {}

    for _, state in reviews:
        statuses[state.status] = statuses.get(state.status, 0) + 1

    print("Statuses:")

    for status, count in sorted(statuses.items()):
        print(f"- {status}: {count}")

    print("Tasks:")

    for _, state in reviews:
        print(f"- {state.task}")


def clear_pending_review(thread_id: str):
    if clear_review_state(thread_id):
        print(f"Cleared review checkpoint: {thread_id}")
        return

    print(f"No review checkpoint found: {thread_id}")


def show_review_details(thread_id: str):
    try:
        state = load_review_state(thread_id)
    except RuntimeError as e:
        print(f"FAILED: {e}")
        return

    print(f"Thread ID: {thread_id}")
    print(f"Task: {state.task}")
    print(f"Status: {state.status}")
    print(f"Iteration: {state.iteration}")
    print(f"Candidate files: {len(state.candidate_files)}")

    for path in sorted(state.candidate_files):
        print(f"- {path}")

    if state.errors:
        print(f"Errors: {len(state.errors)}")
        print(state.errors[-1])
    else:
        print("Errors: none")


def show_review_diff(thread_id: str):
    try:
        state = load_review_state(thread_id)
    except RuntimeError as e:
        print(f"FAILED: {e}")
        return

    show_project_diff(state.original_files, state.candidate_files)
