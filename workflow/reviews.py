from pathlib import Path

from engine.schemas import AgentState

REVIEW_DIR = Path(".workflow") / "reviews"


def build_review_path(thread_id: str) -> Path:
    return REVIEW_DIR / f"{thread_id}.json"


def save_review_state(thread_id: str, state: AgentState):
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    build_review_path(thread_id).write_text(
        state.model_dump_json(indent=2),
        encoding="utf-8",
    )


def load_review_state(thread_id: str) -> AgentState:
    path = build_review_path(thread_id)

    if not path.exists():
        raise RuntimeError(
            f"No review checkpoint found for thread_id: {thread_id}"
        )

    return AgentState.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def list_review_states() -> list[tuple[str, AgentState]]:
    if not REVIEW_DIR.exists():
        return []

    reviews = []

    for path in sorted(REVIEW_DIR.glob("*.json")):
        try:
            state = AgentState.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except ValueError as e:
            raise RuntimeError(
                f"Invalid review checkpoint: {path}"
            ) from e

        reviews.append((path.stem, state))

    return reviews


def delete_review_state(thread_id: str):
    path = build_review_path(thread_id)

    if path.exists():
        path.unlink()


def clear_review_state(thread_id: str) -> bool:
    path = build_review_path(thread_id)

    if not path.exists():
        return False

    path.unlink()
    return True
