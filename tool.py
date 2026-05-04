import requests
import shutil
import ast
import subprocess
import os
import difflib
import argparse


APP_FILE_PATH = "demo_app/main.py"
TEST_FILE_PATH = "demo_app/test_main.py"
BACKUP_PATHS = {
    APP_FILE_PATH: "demo_app/backups/main.py.bak",
    TEST_FILE_PATH: "demo_app/backups/test_main.py.bak",
}
MODEL = "qwen2.5-coder"

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


def write_project_files(files: dict[str, str]):
    for path, code in files.items():
        write_file(path, code)


def parse_generated_files(text: str) -> dict[str, str]:
    files = {}
    current_path = None
    current_lines = []

    for line in text.splitlines():
        if line.strip().startswith("```"):
            continue

        if line.startswith("=== ") and line.endswith(" ==="):
            if current_path is not None:
                files[current_path] = "\n".join(current_lines).strip() + "\n"

            current_path = line.removeprefix("=== ").removesuffix(" ===").strip()
            current_lines = []
        elif current_path is not None:
            current_lines.append(line)

    if current_path is not None:
        files[current_path] = "\n".join(current_lines).strip() + "\n"

    required_paths = {APP_FILE_PATH, TEST_FILE_PATH}
    missing_paths = required_paths - set(files)
    extra_paths = set(files) - required_paths

    if missing_paths:
        raise ValueError(f"Missing files in model response: {sorted(missing_paths)}")

    if extra_paths:
        raise ValueError(f"Unexpected files in model response: {sorted(extra_paths)}")

    return files


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


def generate_code(task, files, error_context):
    file_context = "\n\n".join(
        f"=== {path} ===\n{code}"
        for path, code in files.items()
    )

    prompt = f"""
You are a senior Python developer.

Modify the FastAPI app and its tests according to the task.

Return ONLY the full updated files in this exact format:

=== demo_app/main.py ===
<full updated app file>

=== demo_app/test_main.py ===
<full updated test file>

Do NOT use markdown.
Always add or update tests for the feature you implement.
Keep existing tests unless the task explicitly requires changing behavior.

Do not remove existing endpoints unless the task explicitly asks for removal.
If a route already exists, keep it exactly unless the task asks to change it.
When fixing previous errors, preserve all existing routes from the provided files.

Task:
{task}

Previous errors:
{error_context}

Files:
{file_context}
"""

    try:
        # Ask local Ollama to generate full replacement files.
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=120,
        )

        # Convert HTTP errors like 404/500 into readable Python exceptions.
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            "Ollama request failed. Make sure Ollama is running at "
            "http://localhost:11434 and model qwen2.5-coder is installed."
        ) from e

    data = response.json()

    if "response" not in data:
        raise RuntimeError(f"Ollama response does not contain 'response': {data}")

    return parse_generated_files(data["response"])


def check_code(files):
    # syntax check
    for path, code in files.items():
        try:
            ast.parse(code)
        except Exception as e:
            return False, f"Syntax error in {path}:\n{e}"

    write_project_files(files)

    venv_python = os.path.abspath(".venv/Scripts/python.exe")

    # ruff
    ruff_result = subprocess.run(
        [venv_python, "-m", "ruff", "check", "demo_app"],
        capture_output=True,
        text=True
    )

    if ruff_result.returncode == 0:
        print("RUFF: passed")
    else:
        print_command_output("ruff", ruff_result)
        return False, f"Ruff error:\n{ruff_result.stdout}\n{ruff_result.stderr}"

    # pytest
    pytest_result = subprocess.run(
        [venv_python, "-m", "pytest", "-v", "demo_app"],
        capture_output=True,
        text=True
    )

    if pytest_result.returncode == 0:
        passed_count = pytest_result.stdout.count(" PASSED")
        print(f"PYTEST: passed, {passed_count} tests")
    else:
        print_command_output("pytest", pytest_result)
        return False, f"Pytest error:\n{pytest_result.stdout}\n{pytest_result.stderr}"


    result = subprocess.run(
        [venv_python, "-c", "import demo_app.main"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return False, f"Runtime error:\n{result.stderr}"

    return True, ""


def run_agent(task, dry_run=False):
    for source_path, backup_path in BACKUP_PATHS.items():
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy(source_path, backup_path)

    original_files = read_project_files()
    files = original_files
    error_context = ""

    for i in range(MAX_ITERATIONS):
        print(f"\n--- ITERATION {i+1} ---")

        try:
            new_files = generate_code(task, files, error_context)
        except Exception as e:
            error_context = f"Code generation failed:\n{e}"
            print("FAILED:")
            print(error_context)
            continue
        # Reject generated code that removes existing routes.
        old_routes = extract_get_routes(files[APP_FILE_PATH])
        new_routes = extract_get_routes(new_files[APP_FILE_PATH])
        removed_routes = old_routes - new_routes

        if removed_routes:
            error_context = (
                "Generated code removed existing routes, which is not allowed "
                f"unless the task explicitly asks for it: {sorted(removed_routes)}"
            )
            print("FAILED:")
            print(error_context)
            continue

        # First check that the generated app still passes the original tests.
        baseline_files = {
            APP_FILE_PATH: new_files[APP_FILE_PATH],
            TEST_FILE_PATH: original_files[TEST_FILE_PATH],
        }

        ok, error = check_code(baseline_files)

        if not ok:
            error_context = (
                "Generated app code does not pass the original tests. "
                "Do not change existing behavior unless the task explicitly asks for it.\n"
                f"{error}"
            )
            print("FAILED:")
            print(error_context)
            continue

        ok, error = check_code(new_files)

        if ok:
            write_project_files(original_files)

            show_project_diff(original_files, new_files)

            if dry_run:
                print("DRY RUN: changes were not applied")
                return

            answer = input("\nApply changes? [y/N]: ").strip().lower()

            if answer != "y":
                print("Changes rejected")
                return

            write_project_files(new_files)

            print("SUCCESS: Code updated")
            return

        print("FAILED:")
        print(error)

        error_context = error
        files = new_files

    print("\nFAILED AFTER MAX ITERATIONS")
    print("Restoring backup")

    for source_path, backup_path in BACKUP_PATHS.items():
        shutil.copy(backup_path, source_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    task = input("Task: ").strip()

    if not task:
        print("Task is empty")
    else:
        run_agent(task, dry_run=args.dry_run)
