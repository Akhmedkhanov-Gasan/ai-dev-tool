from engine.project_files import read_project_files, write_project_files
from tools.result import ToolResult


def read_project_files_tool() -> ToolResult:
    files = read_project_files()

    return ToolResult(
        ok=True,
        name="read_project_files",
        message=f"Read {len(files)} project files",
        data={"files": files},
    )


def write_project_files_tool(files: dict[str, str]) -> ToolResult:
    write_project_files(files)

    return ToolResult(
        ok=True,
        name="write_project_files",
        message=f"Wrote {len(files)} project files",
        data={"files": files},
    )
