from engine.validation import check_code
from tools.result import ToolResult


def run_validation_tool(files, original_files) -> ToolResult:
    result = check_code(files, original_files)

    if result.ok:
        message = f"Validation passed: {result.phase}"
    else:
        message = f"Validation failed during {result.phase}"

    return ToolResult(
        ok=result.ok,
        name="run_validation",
        message=message,
        data={"validation_result": result},
    )
