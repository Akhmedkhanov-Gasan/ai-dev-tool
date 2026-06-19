import argparse
import difflib
import os
import shutil
import sys

from dotenv import load_dotenv

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
from workflow import run_agent_workflow

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


def review_candidate(state: AgentState, dry_run: bool) -> str:
    show_project_diff(state.original_files, state.candidate_files)

    if dry_run:
        return "reject"

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


def run_agent(task, dry_run=False):
    print(f"MODEL: {get_model()}")
    print(f"PROVIDER_URL: {get_provider_url()}")
    print(f"DRY_RUN: {dry_run}")

    for source_path, backup_path in BACKUP_PATHS.items():
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy(source_path, backup_path)

    original_files = read_project_files()

    state = AgentState(
        task=task,
        original_files=original_files,
        current_files=original_files,
        retrieved_context=retrieve_project_context(task),
        agent_rules=read_agent_rules(),
        max_iterations=MAX_ITERATIONS,
    )

    state = run_agent_workflow(
        state,
        on_update=print_workflow_update,
        on_review=lambda review_state: review_candidate(
            review_state,
            dry_run,
        ),
    )

    if dry_run and state.status == "rejected":
        state.status = "dry_run_completed"
        print("DRY RUN: changes were not applied")
        print_success_summary(
            state,
            dry_run,
            "dry-run completed",
        )
        return

    if state.status == "rejected":
        print("Changes rejected")
        print_success_summary(
            state,
            dry_run,
            "rejected",
        )
        return

    if state.status == "approved":
        write_project_files(state.candidate_files)
        state.status = "applied"

        print("SUCCESS: Code updated")
        print_success_summary(
            state,
            dry_run,
            "applied",
        )
        return

    print("\nFAILED AFTER MAX ITERATIONS")
    print("Restoring backup")

    if state.errors:
        print("\nLast error:")
        print(state.errors[-1])

    print("\n--- RUN SUMMARY ---")
    print("Status: failed")
    print(f"Iterations: {state.iteration}")
    print(f"Final error phase: {state.final_error_phase or 'unknown'}")
    print(f"Dry run: {dry_run}")

    restore_backups()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("args", nargs="*", help="Agent task or index/search command")
    args = parser.parse_args()

    if args.args and args.args[0] == "index":
        indexed_chunks = index_project()
        print(f"Indexed {indexed_chunks} project chunks")
        sys.exit(0)

    if args.args and args.args[0] == "search":
        query = " ".join(args.args[1:]).strip()

        if not query:
            print("Search query is empty")
            sys.exit(1)

        results = search_project(query, limit=args.limit)

        if not results:
            print("No results")
            sys.exit(0)

        for result in results:
            print(f"\n--- {result['path']}#{result['chunk_index']} ---")
            print(result["snippet"])

        sys.exit(0)

    task = " ".join(args.args).strip()

    if not task:
        task = input("Task: ").strip()

    if not task:
        print("Task is empty")
    else:
        run_agent(task, dry_run=args.dry_run)
