from engine.schemas import AgentState
from runtime import agent_runner
from tools.result import ToolResult


def test_build_initial_state_reads_files_through_tool(monkeypatch):
    files = {
        "demo_app/main.py": "app",
        "demo_app/test_main.py": "tests",
    }

    monkeypatch.setattr(
        agent_runner,
        "read_project_files_tool",
        lambda: ToolResult(
            ok=True,
            name="read_project_files",
            data={"files": files},
        ),
    )
    monkeypatch.setattr(
        agent_runner,
        "retrieve_project_context",
        lambda task: "retrieved context",
    )
    monkeypatch.setattr(
        agent_runner,
        "read_agent_rules",
        lambda: "rules",
    )

    state = agent_runner.build_initial_state("Add endpoint")

    assert state.task == "Add endpoint"
    assert state.original_files == files
    assert state.current_files == files
    assert state.retrieved_context == "retrieved context"
    assert state.agent_rules == "rules"


def test_run_review_only_prints_review_diff(monkeypatch, capsys):
    state = AgentState(
        task="Add endpoint",
        original_files={"demo_app/main.py": "old app"},
        current_files={"demo_app/main.py": "old app"},
        candidate_files={"demo_app/main.py": "new app"},
        status="human_review_required",
    )

    monkeypatch.setattr(
        agent_runner,
        "build_initial_state",
        lambda task: state,
    )
    monkeypatch.setattr(
        agent_runner,
        "start_agent_workflow",
        lambda state, thread_id, on_update: state,
    )

    agent_runner.run_review_only("Add endpoint")

    output = capsys.readouterr().out

    assert "THREAD_ID:" in output
    assert "--- DIFF: demo_app/main.py ---" in output
    assert "-old app" in output
    assert "+new app" in output
    assert "Review required" in output
