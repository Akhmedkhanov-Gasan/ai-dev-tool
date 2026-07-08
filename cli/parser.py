import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--review-only", action="store_true")
    parser.add_argument("--list-reviews", action="store_true")
    parser.add_argument("--review-summary", action="store_true")
    parser.add_argument("--clear-review")
    parser.add_argument("--show-review")
    parser.add_argument("--diff-review")
    parser.add_argument("--resume-thread")
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--reject", action="store_true")
    parser.add_argument("--dry-run-review", action="store_true")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("args", nargs="*", help="Agent task or index/search command")

    return parser
