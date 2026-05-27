import ast
import subprocess
import sys

from engine.schemas import ValidationResult

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


def check_code(files, original_files, write_project_files):
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