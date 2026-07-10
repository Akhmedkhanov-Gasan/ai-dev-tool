import sys

from cli.commands import (
    AgentCommandHandlers,
    handle_cli_args,
    run_task_from_args,
)
from cli.parser import build_parser
from runtime.agent_runner import (
    run_agent,
    run_resume_review,
    run_review_only,
)


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    handlers = AgentCommandHandlers(
        run_agent=run_agent,
        run_review_only=run_review_only,
        run_resume_review=run_resume_review,
    )
    exit_code = handle_cli_args(args, handlers)

    if exit_code is None:
        run_task_from_args(args, handlers)
    else:
        sys.exit(exit_code)
