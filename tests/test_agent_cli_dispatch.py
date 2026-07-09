from cli.commands import (
    AgentCommandHandlers,
    handle_cli_args,
    run_task_from_args,
)
from cli.parser import build_parser


def make_handlers(**overrides) -> AgentCommandHandlers:
    handlers = {
        "run_agent": lambda task, dry_run: None,
        "run_review_only": lambda task: None,
        "run_resume_review": lambda thread_id, decision: None,
    }
    handlers.update(overrides)
    return AgentCommandHandlers(**handlers)


def test_handle_cli_args_dispatches_review_summary(monkeypatch):
    parser = build_parser()
    args = parser.parse_args(["--review-summary"])
    called = {}

    def fake_show_review_summary():
        called["review_summary"] = True

    monkeypatch.setattr(
        "cli.commands.show_review_summary",
        fake_show_review_summary,
    )

    assert handle_cli_args(args, make_handlers()) == 0
    assert called == {"review_summary": True}


def test_handle_cli_args_leaves_agent_task_unhandled():
    parser = build_parser()
    args = parser.parse_args(["Add endpoint"])

    assert handle_cli_args(args, make_handlers()) is None


def test_handle_cli_args_returns_error_for_invalid_resume_decision(capsys):
    parser = build_parser()
    args = parser.parse_args(["--resume-thread", "thread-1"])

    assert handle_cli_args(args, make_handlers()) == 1

    output = capsys.readouterr().out

    assert "Choose exactly one resume decision" in output


def test_run_task_from_args_runs_review_only(monkeypatch):
    parser = build_parser()
    args = parser.parse_args(["--review-only", "Add endpoint"])
    called = {}

    def fake_run_review_only(task):
        called["task"] = task

    handlers = make_handlers(run_review_only=fake_run_review_only)

    run_task_from_args(args, handlers)

    assert called == {"task": "Add endpoint"}
