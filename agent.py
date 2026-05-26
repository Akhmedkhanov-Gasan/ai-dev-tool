import shutil
import ast
import subprocess
import os
import difflib
import argparse
import sys
from dotenv import load_dotenv

from engine.index import index_project, search_project
from engine.retrieval import retrieve_project_context
from engine.generated_files import parse_generated_files
from engine.schemas import AgentState, ValidationResult
from engine.llm import get_model, get_provider_url, request_model

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


def extract_get_routes(code: str) -> set[str]:
    # Collect existing GET routes so the model cannot silently remove API endpoints.
    routes = set()

    for line in code.splitlines():
        line = line.strip()

        if line.startswith('@app.get("') and line.endswith('")'):
            route = line.removeprefix('@app.get("').removesuffix('")')
            routes.add(route)

    return routes


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


def print_command_output(name: str, result: subprocess.CompletedProcess):
    print(f"\n--- {name.upper()} OUTPUT ---")

    output = result.stdout.strip()
    error = result.stderr.strip()

    if output:
        print(output)

    if error:
        print(error)

    if not output and not error:
        print("No output")


def generate_code(task, files, error_context, project_context):
    file_context = "\n\n".join(
        f"=== {path} ===\n{code}"
        for path, code in files.items()
    )
    agent_rules = read_agent_rules()

    prompt = f"""
You are a senior Python developer.

Modify the FastAPI app and its tests according to the task.

Follow these project rules:

{agent_rules}

Return ONLY valid JSON.
Do not wrap the JSON in Markdown.
Do not add explanations before or after the JSON.

The JSON must match this schema:

{{
  "files": [
    {{
      "path": "demo_app/main.py",
      "content": "full updated content of demo_app/main.py"
    }},
    {{
      "path": "demo_app/test_main.py",
      "content": "full updated content of demo_app/test_main.py"
    }}
  ]
}}

Both files are required.
Return full file contents, not a diff or patch.

Always add or update tests for the feature you implement.
Keep existing tests unless the task explicitly requires changing behavior.

Do not remove existing endpoints unless the task explicitly asks for removal.
If a route already exists, keep it exactly unless the task asks to change it.
When fixing previous errors, preserve all existing routes from the provided files.

Preserve all imports required by existing code.

Do not weaken existing behavior or replace dynamic behavior with hardcoded values.

When Previous errors contains Ruff F821, fix missing imports before making any other changes.

Task:
{task}

Previous errors:
{error_context}

Relevant project context:
{project_context}

Files:
{file_context}

"""

    model_response = request_model(prompt)

    return parse_generated_files(model_response)


def check_code(files):
    # Syntax can be checked in memory before touching files on disk.
    for path, code in files.items():
        try:
            ast.parse(code)
        except Exception as e:
            return ValidationResult(
                ok=False,
                phase="syntax",
                message=f"Syntax error in {path}:\n{e}",
            )

    original_files = read_project_files()

    try:
        write_project_files(files)

        python_executable = sys.executable

        # Ruff validates style and catches simple static errors.
        ruff_result = subprocess.run(
            [python_executable, "-m", "ruff", "check", "demo_app"],
            capture_output=True,
            text=True,
        )

        if ruff_result.returncode == 0:
            print("RUFF: passed")
        else:
            print_command_output("ruff", ruff_result)
            return ValidationResult(
                ok=False,
                phase="ruff",
                message=f"Ruff error:\n{ruff_result.stdout}\n{ruff_result.stderr}",
            )

        # Pytest validates application behavior through tests.
        pytest_result = subprocess.run(
            [python_executable, "-m", "pytest", "-v", "demo_app"],
            capture_output=True,
            text=True,
        )

        if pytest_result.returncode == 0:
            passed_count = pytest_result.stdout.count(" PASSED")
            print(f"PYTEST: passed, {passed_count} tests")
        else:
            print_command_output("pytest", pytest_result)
            return ValidationResult(
                ok=False,
                phase="pytest",
                message=f"Pytest error:\n{pytest_result.stdout}\n{pytest_result.stderr}",
            )

        result = subprocess.run(
            [python_executable, "-c", "import demo_app.main"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return ValidationResult(
                ok=False,
                phase="runtime",
                message=f"Runtime error:\n{result.stderr}",
            )

        return ValidationResult(ok=True, phase="passed")
    finally:
        # Validation writes candidate files temporarily; always restore the workspace.
        write_project_files(original_files)


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

    for i in range(MAX_ITERATIONS):
        print(f"\n--- ITERATION {i + 1} ---")
        error_context = "\n\n".join(state.errors)

        try:
            new_files = generate_code(
                task,
                state.current_files,
                error_context,
                state.retrieved_context,
            )
        except Exception as e:
            final_error_phase = "code generation"
            error_message = f"Code generation failed:\n{e}"
            state.errors.append(error_message)
            print("FAILED:")
            print(error_message)
            continue
        # Reject generated code that removes existing routes.
        old_routes = extract_get_routes(state.current_files[APP_FILE_PATH])
        new_routes = extract_get_routes(new_files[APP_FILE_PATH])
        removed_routes = old_routes - new_routes

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
        baseline_result = check_code(baseline_files)

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
        candidate_result = check_code(new_files)

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
