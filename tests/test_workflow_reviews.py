import pytest

from engine.schemas import AgentState
from workflow import reviews


def make_state(task: str = "task") -> AgentState:
    return AgentState(
        task=task,
        original_files={"demo_app/main.py": "old app"},
        current_files={"demo_app/main.py": "old app"},
        candidate_files={"demo_app/main.py": "new app"},
        iteration=1,
        status="human_review_required",
    )


def test_review_state_can_be_saved_loaded_and_deleted(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(reviews, "REVIEW_DIR", tmp_path)

    state = make_state()

    reviews.save_review_state("thread-1", state)

    loaded_state = reviews.load_review_state("thread-1")

    assert loaded_state == state

    reviews.delete_review_state("thread-1")

    with pytest.raises(RuntimeError, match="No review checkpoint found"):
        reviews.load_review_state("thread-1")


def test_list_review_states_returns_saved_reviews(tmp_path, monkeypatch):
    monkeypatch.setattr(reviews, "REVIEW_DIR", tmp_path)

    reviews.save_review_state("thread-b", make_state(task="second"))
    reviews.save_review_state("thread-a", make_state(task="first"))

    saved_reviews = reviews.list_review_states()

    assert saved_reviews == [
        ("thread-a", make_state(task="first")),
        ("thread-b", make_state(task="second")),
    ]


def test_list_review_states_returns_empty_list_when_directory_is_missing(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(reviews, "REVIEW_DIR", tmp_path / "missing")

    assert reviews.list_review_states() == []
