from cli.parser import build_parser


def test_build_parser_reads_review_flags():
    parser = build_parser()

    args = parser.parse_args(
        [
            "--review-only",
            "--dry-run",
            "Add endpoint",
        ]
    )

    assert args.review_only is True
    assert args.dry_run is True
    assert args.args == ["Add endpoint"]


def test_build_parser_reads_resume_decision_flags():
    parser = build_parser()

    args = parser.parse_args(
        [
            "--resume-thread",
            "thread-1",
            "--dry-run-review",
        ]
    )

    assert args.resume_thread == "thread-1"
    assert args.dry_run_review is True
