import pytest

from engine.schemas import ValidationResult
from tools.result import ToolResult
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
