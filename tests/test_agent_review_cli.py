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


def test_show_review_summary_prints_empty_count(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(reviews, "REVIEW_DIR", tmp_path / "missing")

    agent.show_review_summary()

    output = capsys.readouterr().out

    assert output == "Pending reviews: 0\n"


def test_show_review_summary_prints_status_counts_and_tasks(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(reviews, "REVIEW_DIR", tmp_path)

    reviews.save_review_state(
        "thread-1",
        AgentState(
            task="Add info endpoint",
            original_files={},
            current_files={},
            status="human_review_required",
        ),
    )
    reviews.save_review_state(
        "thread-2",
        AgentState(
            task="Update health endpoint",
            original_files={},
            current_files={},
            status="human_review_required",
        ),
    )

    agent.show_review_summary()

    output = capsys.readouterr().out

    assert "Pending reviews: 2" in output
    assert "- human_review_required: 2" in output
    assert "- Add info endpoint" in output
    assert "- Update health endpoint" in output
