import agent
from cli.parser import build_parser


def test_handle_cli_args_dispatches_review_summary(monkeypatch):
    parser = build_parser()
    args = parser.parse_args(["--review-summary"])
    called = {}

    def fake_show_review_summary():
        called["review_summary"] = True

    monkeypatch.setattr(
        agent,
        "show_review_summary",
        fake_show_review_summary,
    )

    assert agent.handle_cli_args(args) == 0
    assert called == {"review_summary": True}


def test_handle_cli_args_leaves_agent_task_unhandled():
    parser = build_parser()
    args = parser.parse_args(["Add endpoint"])

    assert agent.handle_cli_args(args) is None


def test_handle_cli_args_returns_error_for_invalid_resume_decision(capsys):
    parser = build_parser()
    args = parser.parse_args(["--resume-thread", "thread-1"])

    assert agent.handle_cli_args(args) == 1

    output = capsys.readouterr().out

    assert "Choose exactly one resume decision" in output


def test_run_task_from_args_runs_review_only(monkeypatch):
    parser = build_parser()
    args = parser.parse_args(["--review-only", "Add endpoint"])
    called = {}

    def fake_run_review_only(task):
        called["task"] = task

    monkeypatch.setattr(agent, "run_review_only", fake_run_review_only)

    agent.run_task_from_args(args)

    assert called == {"task": "Add endpoint"}
