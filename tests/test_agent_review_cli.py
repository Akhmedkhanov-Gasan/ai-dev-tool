import agent

from engine.schemas import AgentState
from workflow import reviews


def test_show_review_diff_prints_saved_candidate_diff(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(reviews, "REVIEW_DIR", tmp_path)

    state = AgentState(
        task="Add endpoint",
        original_files={"demo_app/main.py": "old app"},
        current_files={"demo_app/main.py": "old app"},
        candidate_files={"demo_app/main.py": "new app"},
        status="human_review_required",
    )

    reviews.save_review_state("thread-1", state)

    agent.show_review_diff("thread-1")

    output = capsys.readouterr().out

    assert "--- DIFF: demo_app/main.py ---" in output
    assert "-old app" in output
    assert "+new app" in output
