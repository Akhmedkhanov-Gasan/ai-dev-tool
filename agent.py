import os
import shutil
import sys
from uuid import uuid4

from dotenv import load_dotenv

from cli.parser import build_parser
from engine.index import index_project, search_project
from engine.llm import get_model, get_provider_url
from engine.project_files import (
    APP_FILE_PATH,
    TEST_FILE_PATH,
    read_file,
    read_project_files,
    write_project_files,
)
from engine.retrieval import retrieve_project_context
from engine.schemas import AgentState
from workflow import (
    resume_agent_workflow,
    run_agent_workflow,
    start_agent_workflow,
)
from workflow.review_cli import (
    clear_pending_review,
    show_pending_reviews,
    show_project_diff,
    show_review_details,
    show_review_diff,
    show_review_summary,
)

load_dotenv()

RULES_FILE_PATH = "AGENT_RULES.md"
BACKUP_PATHS = {
    APP_FILE_PATH: "demo_app/backups/main.py.bak",
    TEST_FILE_PATH: "demo_app/backups/test_main.py.bak",
}
MAX_ITERATIONS = 3


def read_agent_rules() -> str:
    if not os.path.exists(RULES_FILE_PATH):
        return "No project-specific agent rules."

    return read_file(RULES_FILE_PATH)


def review_candidate(state: AgentState, dry_run: bool) -> str:
    show_project_diff(state.original_files, state.candidate_files)

    if dry_run:
        return "dry_run"

    answer = input("\nApply changes? [y/N]: ").strip().lower()

    return "approve" if answer == "y" else "reject"


def print_workflow_update(node_name: str, update: dict):
    iteration = update.get("iteration")
    status = update.get("status", "completed")

    if node_name == "generate_candidate" and iteration is not None:
        print(f"\n--- ITERATION {iteration} ---")

    print(f"{node_name}: {status}")

    if status.endswith("_failed"):
        errors = update.get("errors", [])

        if errors:
            print(errors[-1])


def print_success_summary(state: AgentState, dry_run: bool, status: str):
    print("\n--- RUN SUMMARY ---")
    print(f"Status: {status}")
    print(f"Iterations: {state.iteration}")
    print("Baseline validation: passed")
    print("Candidate validation: passed")
    print(f"Dry run: {dry_run}")


def restore_backups():
    for source_path, backup_path in BACKUP_PATHS.items():
        shutil.copy(backup_path, source_path)


def build_initial_state(task: str) -> AgentState:
    original_files = read_project_files()

    return AgentState(
        task=task,
        original_files=original_files,
        current_files=original_files,
        retrieved_context=retrieve_project_context(task),
        agent_rules=read_agent_rules(),
        max_iterations=MAX_ITERATIONS,
    )


def handle_workflow_action(state: AgentState, dry_run: bool):
    action = state.pending_action

    if action == "dry_run":
        print("DRY RUN: changes were not applied")
        print_success_summary(
            state,
            dry_run,
            "dry-run completed",
        )
        return

    if action == "reject":
        print("Changes rejected")
        print_success_summary(
            state,
            dry_run,
            "rejected",
        )
        return

    if action == "apply_changes":
        write_project_files(state.candidate_files)
        state.status = "applied"

        print("SUCCESS: Code updated")
        print_success_summary(
            state,
            dry_run,
            "applied",
        )
        return

    print("\nFAILED: unexpected workflow result")
    print(f"Status: {state.status}")

    if state.errors:
        print("\nLast error:")
        print(state.errors[-1])

    print("\n--- RUN SUMMARY ---")
    print("Status: failed")
    print(f"Iterations: {state.iteration}")
    print(f"Final error phase: {state.final_error_phase or 'unknown'}")
    print(f"Dry run: {dry_run}")

    if action == "restore_backup":
        restore_backups()


def run_agent(task, dry_run=False):
    print(f"MODEL: {get_model()}")
    print(f"PROVIDER_URL: {get_provider_url()}")
    print(f"DRY_RUN: {dry_run}")
    thread_id = str(uuid4())

    for source_path, backup_path in BACKUP_PATHS.items():
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy(source_path, backup_path)

    state = build_initial_state(task)

    state = run_agent_workflow(
        state,
        thread_id=thread_id,
        on_update=print_workflow_update,
        on_review=lambda review_state: review_candidate(
            review_state,
            dry_run,
        ),
    )

    handle_workflow_action(state, dry_run)


def run_review_only(task: str):
    thread_id = str(uuid4())

    print(f"MODEL: {get_model()}")
    print(f"PROVIDER_URL: {get_provider_url()}")
    print(f"THREAD_ID: {thread_id}")

    state = build_initial_state(task)

    try:
        state = start_agent_workflow(
            state,
            thread_id=thread_id,
            on_update=print_workflow_update,
        )
    except RuntimeError as e:
        print(f"\nFAILED: {e}")
        return

    if state.status != "human_review_required":
        print("\nWorkflow finished before human review")
        print(f"Status: {state.status}")

        if state.errors:
            print("\nLast error:")
            print(state.errors[-1])

        if state.pending_action == "restore_backup":
            print("\nNo review checkpoint was created.")

        return

    show_project_diff(state.original_files, state.candidate_files)

    print("\nReview required")
    print(f"Thread ID: {thread_id}")


def run_resume_review(thread_id: str, decision: str):
    print(f"RESUME_THREAD: {thread_id}")
    print(f"DECISION: {decision}")

    try:
        state = resume_agent_workflow(
            thread_id=thread_id,
            decision=decision,
            on_update=print_workflow_update,
        )
    except RuntimeError as e:
        print(f"\nFAILED: {e}")
        return

    handle_workflow_action(
        state,
        dry_run=decision == "dry_run",
    )


def handle_cli_args(args) -> int | None:
    if args.args and args.args[0] == "index":
        indexed_chunks = index_project()
        print(f"Indexed {indexed_chunks} project chunks")
        return 0

    if args.args and args.args[0] == "search":
        query = " ".join(args.args[1:]).strip()

        if not query:
            print("Search query is empty")
            return 1

        results = search_project(query, limit=args.limit)

        if not results:
            print("No results")
            return 0

        for result in results:
            print(f"\n--- {result['path']}#{result['chunk_index']} ---")
            print(result["snippet"])

        return 0

    if args.list_reviews:
        show_pending_reviews()
        return 0

    if args.review_summary:
        show_review_summary()
        return 0

    if args.clear_review:
        clear_pending_review(args.clear_review)
        return 0

    if args.show_review:
        show_review_details(args.show_review)
        return 0

    if args.diff_review:
        show_review_diff(args.diff_review)
        return 0

    if args.resume_thread:
        decisions = [
            args.approve,
            args.reject,
            args.dry_run_review,
        ]

        if sum(decisions) != 1:
            print(
                "Choose exactly one resume decision: "
                "--approve, --reject, or --dry-run-review"
            )
            return 1

        if args.approve:
            decision = "approve"
        elif args.reject:
            decision = "reject"
        else:
            decision = "dry_run"

        run_resume_review(args.resume_thread, decision)
        return 0

    return None


def run_task_from_args(args):
    task = " ".join(args.args).strip()

    if not task:
        task = input("Task: ").strip()

    if not task:
        print("Task is empty")
    elif args.review_only:
        run_review_only(task)
    else:
        run_agent(task, dry_run=args.dry_run)


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    exit_code = handle_cli_args(args)

    if exit_code is None:
        run_task_from_args(args)
    else:
        sys.exit(exit_code)
