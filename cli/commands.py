from collections.abc import Callable
from dataclasses import dataclass

from engine.index import index_project, search_project
from workflow.review_cli import (
    clear_pending_review,
    show_pending_reviews,
    show_review_details,
    show_review_diff,
    show_review_summary,
)


@dataclass(frozen=True)
class AgentCommandHandlers:
    run_agent: Callable[[str, bool], None]
    run_review_only: Callable[[str], None]
    run_resume_review: Callable[[str, str], None]


def handle_cli_args(args, handlers: AgentCommandHandlers) -> int | None:
    if args.args and args.args[0] == "index":
        indexed_chunks = index_project()
        print(f"Indexed {indexed_chunks} project chunks")
        return 0

    if args.args and args.args[0] == "search":
        query = " ".join(args.args[1:]).strip()

        if not query:
            print("Search query is empty")
            return 1

        results = search_project(query, limit=args.limit)

        if not results:
            print("No results")
            return 0

        for result in results:
            print(f"\n--- {result['path']}#{result['chunk_index']} ---")
            print(result["snippet"])

        return 0

    if args.list_reviews:
        show_pending_reviews()
        return 0

    if args.review_summary:
        show_review_summary()
        return 0

    if args.clear_review:
        clear_pending_review(args.clear_review)
        return 0

    if args.show_review:
        show_review_details(args.show_review)
        return 0

    if args.diff_review:
        show_review_diff(args.diff_review)
        return 0

    if args.resume_thread:
        decisions = [
            args.approve,
            args.reject,
            args.dry_run_review,
        ]

        if sum(decisions) != 1:
            print(
                "Choose exactly one resume decision: "
                "--approve, --reject, or --dry-run-review"
            )
            return 1

        if args.approve:
            decision = "approve"
        elif args.reject:
            decision = "reject"
        else:
            decision = "dry_run"

        handlers.run_resume_review(args.resume_thread, decision)
        return 0

    return None


def run_task_from_args(args, handlers: AgentCommandHandlers):
    task = " ".join(args.args).strip()

    if not task:
        task = input("Task: ").strip()

    if not task:
        print("Task is empty")
    elif args.review_only:
        handlers.run_review_only(task)
    else:
        handlers.run_agent(task, args.dry_run)
