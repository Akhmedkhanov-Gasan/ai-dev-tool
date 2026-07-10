from engine.schemas import AgentState
from runtime import agent_runner


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
