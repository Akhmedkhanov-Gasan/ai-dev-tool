from engine.project_files import read_project_files
from tools.result import ToolResult


def read_project_files_tool() -> ToolResult:
    files = read_project_files()

    return ToolResult(
        ok=True,
        name="read_project_files",
        message=f"Read {len(files)} project files",
        data={"files": files},
    )
