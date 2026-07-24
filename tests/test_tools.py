import pytest

from engine.schemas import ValidationResult
from tools.result import ToolResult
from tools import project_tools
from tools import route_tools
from tools import validation_tools


def test_tool_result_stores_tool_data():
    result = ToolResult(
        ok=True,
        name="example_tool",
        message="done",
        data={"value": 1},
    )

    assert result.ok is True
    assert result.name == "example_tool"
    assert result.message == "done"
    assert result.data == {"value": 1}


def test_tool_result_rejects_empty_name():
    with pytest.raises(ValueError, match="name must not be empty"):
        ToolResult(ok=True, name=" ")


def test_run_validation_tool_wraps_success(monkeypatch):
    validation_result = ValidationResult(ok=True, phase="passed")

    def fake_check_code(files, original_files):
        assert files == {"demo_app/main.py": "app"}
        assert original_files == {"demo_app/main.py": "original"}
        return validation_result

    monkeypatch.setattr(validation_tools, "check_code", fake_check_code)

    result = validation_tools.run_validation_tool(
        {"demo_app/main.py": "app"},
        {"demo_app/main.py": "original"},
    )

    assert result.ok is True
    assert result.name == "run_validation"
    assert result.message == "Validation passed: passed"
    assert result.data["validation_result"] is validation_result


def test_run_validation_tool_wraps_failure(monkeypatch):
    validation_result = ValidationResult(
        ok=False,
        phase="pytest",
        message="tests failed",
    )

    monkeypatch.setattr(
        validation_tools,
        "check_code",
        lambda files, original_files: validation_result,
    )

    result = validation_tools.run_validation_tool({}, {})

    assert result.ok is False
    assert result.name == "run_validation"
    assert result.message == "Validation failed during pytest"
    assert result.data["validation_result"] is validation_result


def test_inspect_removed_routes_tool_wraps_success(monkeypatch):
    def fake_find_removed_get_routes(old_code, new_code):
        assert old_code == "old app"
        assert new_code == "new app"
        return set()

    monkeypatch.setattr(
        route_tools,
        "find_removed_get_routes",
        fake_find_removed_get_routes,
    )

    result = route_tools.inspect_removed_routes_tool("old app", "new app")

    assert result.ok is True
    assert result.name == "inspect_removed_routes"
    assert result.message == "No removed GET routes found"
    assert result.data["removed_routes"] == set()


def test_inspect_removed_routes_tool_wraps_removed_routes(monkeypatch):
    monkeypatch.setattr(
        route_tools,
        "find_removed_get_routes",
        lambda old_code, new_code: {"/health"},
    )

    result = route_tools.inspect_removed_routes_tool("old app", "new app")

    assert result.ok is False
    assert result.name == "inspect_removed_routes"
    assert result.message == "Removed GET routes found: ['/health']"
    assert result.data["removed_routes"] == {"/health"}


def test_read_project_files_tool_wraps_project_files(monkeypatch):
    files = {
        "demo_app/main.py": "app",
        "demo_app/test_main.py": "tests",
    }

    monkeypatch.setattr(
        project_tools,
        "read_project_files",
        lambda: files,
    )

    result = project_tools.read_project_files_tool()

    assert result.ok is True
    assert result.name == "read_project_files"
    assert result.message == "Read 2 project files"
    assert result.data["files"] is files


def test_write_project_files_tool_wraps_project_files(monkeypatch):
    files = {
        "demo_app/main.py": "app",
        "demo_app/test_main.py": "tests",
    }
    captured = {}

    def fake_write_project_files(files_to_write):
        captured["files"] = files_to_write

    monkeypatch.setattr(
        project_tools,
        "write_project_files",
        fake_write_project_files,
    )

    result = project_tools.write_project_files_tool(files)

    assert captured["files"] is files
    assert result.ok is True
    assert result.name == "write_project_files"
    assert result.message == "Wrote 2 project files"
    assert result.data["files"] is files
