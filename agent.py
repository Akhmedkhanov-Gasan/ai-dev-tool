import shutil
import os
import difflib
import argparse
import sys
from dotenv import load_dotenv

from engine.index import index_project, search_project
from engine.retrieval import retrieve_project_context
from engine.schemas import AgentState
from engine.llm import get_model, get_provider_url
from engine.validation import check_code
from engine.generation import generate_code
from engine.routes import find_removed_get_routes

load_dotenv()

APP_FILE_PATH = "demo_app/main.py"
TEST_FILE_PATH = "demo_app/test_main.py"
RULES_FILE_PATH = "AGENT_RULES.md"

BACKUP_PATHS = {
    APP_FILE_PATH: "demo_app/backups/main.py.bak",
    TEST_FILE_PATH: "demo_app/backups/test_main.py.bak",
}


MAX_ITERATIONS = 3


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path: str, code: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)


def read_project_files() -> dict[str, str]:
    return {
        APP_FILE_PATH: read_file(APP_FILE_PATH),
        TEST_FILE_PATH: read_file(TEST_FILE_PATH),
    }


def read_agent_rules() -> str:
    if not os.path.exists(RULES_FILE_PATH):
        return "No project-specific agent rules."

    return read_file(RULES_FILE_PATH)





def write_project_files(files: dict[str, str]):
    for path, code in files.items():
        write_file(path, code)


def show_diff(path: str, old_code: str, new_code: str):
    diff = difflib.unified_diff(
        old_code.splitlines(),
        new_code.splitlines(),
        fromfile=path,
        tofile=f"{path} updated",
        lineterm=""
    )

    print(f"\n--- DIFF: {path} ---")
    print("\n".join(diff))


def show_project_diff(old_files: dict[str, str], new_files: dict[str, str]):
    for path, old_code in old_files.items():
        show_diff(path, old_code, new_files[path])


def run_agent(task, dry_run=False):

    print(f"MODEL: {get_model()}")
    print(f"PROVIDER_URL: {get_provider_url()}")
    print(f"DRY_RUN: {dry_run}")

    for source_path, backup_path in BACKUP_PATHS.items():
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy(source_path, backup_path)

    original_files = read_project_files()
    final_error_phase = ""

    state = AgentState(
        task=task,
        original_files=original_files,
        current_files=original_files,
        retrieved_context=retrieve_project_context(task),
    )
    agent_rules = read_agent_rules()

    for i in range(MAX_ITERATIONS):
        print(f"\n--- ITERATION {i + 1} ---")
        error_context = "\n\n".join(state.errors)

        try:
            new_files = generate_code(
                task,
                state.current_files,
                error_context,
                state.retrieved_context,
                agent_rules,
            )
        except Exception as e:
            final_error_phase = "code generation"
            error_message = f"Code generation failed:\n{e}"
            state.errors.append(error_message)
            print("FAILED:")
            print(error_message)
            continue
        # Reject generated code that removes existing routes.
        removed_routes = find_removed_get_routes(
            state.current_files[APP_FILE_PATH],
            new_files[APP_FILE_PATH],
        )

        if removed_routes:
            final_error_phase = "route protection"
            error_message = (
                "Generated code removed existing routes, which is not allowed "
                f"unless the task explicitly asks for it: {sorted(removed_routes)}"
            )
            state.errors.append(error_message)
            print("FAILED:")
            print(error_message)
            continue

        # First check that the generated app still passes the original tests.
        baseline_files = {
            APP_FILE_PATH: new_files[APP_FILE_PATH],
            TEST_FILE_PATH: original_files[TEST_FILE_PATH],
        }

        print("\n--- BASELINE VALIDATION ---")
        baseline_result = check_code(baseline_files, original_files, write_project_files)

        if not baseline_result.ok:
            final_error_phase = f"baseline validation: {baseline_result.phase}"
            error_message = (
                "Baseline validation failed. Generated app code does not pass the original tests. "
                "Do not change existing behavior unless the task explicitly asks for it.\n"
                f"{baseline_result.message}"
            )
            state.errors.append(error_message)
            print("FAILED:")
            print(error_message)
            continue

        print("\n--- CANDIDATE VALIDATION ---")
        candidate_result = check_code(new_files, original_files, write_project_files)

        if candidate_result.ok:
            show_project_diff(original_files, new_files)

            if dry_run:
                print("DRY RUN: changes were not applied")
                print("\n--- RUN SUMMARY ---")
                print("Status: dry-run completed")
                print(f"Iterations: {i + 1}")
                print("Baseline validation: passed")
                print("Candidate validation: passed")
                print(f"Dry run: {dry_run}")
                return

            answer = input("\nApply changes? [y/N]: ").strip().lower()

            if answer != "y":
                print("Changes rejected")
                print("\n--- RUN SUMMARY ---")
                print("Status: rejected")
                print(f"Iterations: {i + 1}")
                print("Baseline validation: passed")
                print("Candidate validation: passed")
                print(f"Dry run: {dry_run}")
                return

            write_project_files(new_files)

            print("SUCCESS: Code updated")
            print("\n--- RUN SUMMARY ---")
            print("Status: applied")
            print(f"Iterations: {i + 1}")
            print("Baseline validation: passed")
            print("Candidate validation: passed")
            print(f"Dry run: {dry_run}")
            return

        final_error_phase = f"candidate validation: {candidate_result.phase}"

        print("FAILED:")
        print(candidate_result.message)

        state.errors.append(candidate_result.message)
        state.current_files = new_files

    print("\nFAILED AFTER MAX ITERATIONS")
    print("Restoring backup")

    print("\n--- RUN SUMMARY ---")
    print("Status: failed")
    print(f"Iterations: {MAX_ITERATIONS}")
    print(f"Final error phase: {final_error_phase or 'unknown'}")
    print(f"Dry run: {dry_run}")

    for source_path, backup_path in BACKUP_PATHS.items():
        shutil.copy(backup_path, source_path)


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
