import pytest

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
    monkeypatch.delenv("AI_AGENT_PENDING_REVIEW_WARNING_LIMIT", raising=False)

    agent.show_review_summary()

    output = capsys.readouterr().out

    assert output == "Pending reviews: 0\n"


def test_show_review_summary_prints_status_counts_and_tasks(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(reviews, "REVIEW_DIR", tmp_path)
    monkeypatch.delenv("AI_AGENT_PENDING_REVIEW_WARNING_LIMIT", raising=False)

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


def test_show_review_summary_warns_when_review_count_exceeds_limit(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(reviews, "REVIEW_DIR", tmp_path)
    monkeypatch.setenv("AI_AGENT_PENDING_REVIEW_WARNING_LIMIT", "1")

    reviews.save_review_state(
        "thread-1",
        AgentState(
            task="First task",
            original_files={},
            current_files={},
            status="human_review_required",
        ),
    )
    reviews.save_review_state(
        "thread-2",
        AgentState(
            task="Second task",
            original_files={},
            current_files={},
            status="human_review_required",
        ),
    )

    agent.show_review_summary()

    output = capsys.readouterr().out

    assert "Pending reviews: 2" in output
    assert "WARNING: pending review count is above limit: 1" in output


def test_get_pending_review_warning_limit_uses_default(monkeypatch):
    monkeypatch.delenv("AI_AGENT_PENDING_REVIEW_WARNING_LIMIT", raising=False)

    assert agent.get_pending_review_warning_limit() == 5


def test_get_pending_review_warning_limit_reads_env(monkeypatch):
    monkeypatch.setenv("AI_AGENT_PENDING_REVIEW_WARNING_LIMIT", "3")

    assert agent.get_pending_review_warning_limit() == 3


def test_get_pending_review_warning_limit_rejects_invalid_env(monkeypatch):
    monkeypatch.setenv("AI_AGENT_PENDING_REVIEW_WARNING_LIMIT", "many")

    with pytest.raises(RuntimeError, match="must be an integer"):
        agent.get_pending_review_warning_limit()


def test_get_pending_review_warning_limit_rejects_negative_env(monkeypatch):
    monkeypatch.setenv("AI_AGENT_PENDING_REVIEW_WARNING_LIMIT", "-1")

    with pytest.raises(RuntimeError, match="0 or greater"):
        agent.get_pending_review_warning_limit()
