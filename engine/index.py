import re
import sqlite3
from pathlib import Path


DEFAULT_INDEX_PATH = Path(".agent/project_index.sqlite")
INDEXED_SUFFIXES = {".py", ".md", ".txt", ".yml", ".yaml"}
INDEXED_FILENAMES = {"Dockerfile", ".dockerignore"}
SKIPPED_DIRS = {
    ".agent",
    ".git",
    ".idea",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "demo_app/backups",
    "tmp_docs",
}


def should_index_file(path: Path) -> bool:
    return path.name in INDEXED_FILENAMES or path.suffix in INDEXED_SUFFIXES


def is_skipped_path(path: Path) -> bool:
    path_parts = set(path.parts)

    for skipped_dir in SKIPPED_DIRS:
        skipped_parts = set(Path(skipped_dir).parts)

        if skipped_parts.issubset(path_parts):
            return True

    return False


def iter_project_files(root: Path):
    for path in root.rglob("*"):
        relative_path = path.relative_to(root)

        if path.is_dir() or is_skipped_path(relative_path):
            continue

        if should_index_file(path):
            yield relative_path


def chunk_text(text: str, max_lines: int = 80) -> list[str]:
    lines = text.splitlines()
    chunks = []

    for start in range(0, len(lines), max_lines):
        chunk = "\n".join(lines[start:start + max_lines]).strip()

        if chunk:
            chunks.append(chunk)

    return chunks


def connect_index(db_path: Path = DEFAULT_INDEX_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS project_chunks
        USING fts5(path UNINDEXED, chunk_index UNINDEXED, content)
        """
    )
    return connection


def index_project(root: Path = Path("."), db_path: Path = DEFAULT_INDEX_PATH) -> int:
    root = root.resolve()

    with connect_index(db_path) as connection:
        connection.execute("DELETE FROM project_chunks")
        indexed_chunks = 0

        for relative_path in iter_project_files(root):
            full_path = root / relative_path
            content = full_path.read_text(encoding="utf-8")

            for chunk_index, chunk in enumerate(chunk_text(content)):
                connection.execute(
                    """
                    INSERT INTO project_chunks(path, chunk_index, content)
                    VALUES (?, ?, ?)
                    """,
                    (relative_path.as_posix(), chunk_index, chunk),
                )
                indexed_chunks += 1

    return indexed_chunks


def build_search_query(query: str) -> str:
    terms = re.findall(r"[A-Za-z0-9_./:-]+", query)

    if not terms:
        raise ValueError("Search query is empty")

    return " OR ".join(f'"{term}"' for term in terms)


def search_project(
    query: str,
    limit: int = 5,
    db_path: Path = DEFAULT_INDEX_PATH,
) -> list[dict[str, str | int | float]]:
    fts_query = build_search_query(query)

    with connect_index(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                path,
                chunk_index,
                snippet(project_chunks, 2, '[', ']', '...', 16) AS snippet,
                bm25(project_chunks) AS score
            FROM project_chunks
            WHERE project_chunks MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (fts_query, limit),
        ).fetchall()

    return [
        {
            "path": path,
            "chunk_index": chunk_index,
            "snippet": snippet,
            "score": score,
        }
        for path, chunk_index, snippet, score in rows
    ]


def format_search_results(results: list[dict[str, str | int | float]]) -> str:
    if not results:
        return "No relevant project context found."

    blocks = []

    for result in results:
        blocks.append(
            f"--- {result['path']}#{result['chunk_index']} ---\n"
            f"{result['snippet']}"
        )

    return "\n\n".join(blocks)
