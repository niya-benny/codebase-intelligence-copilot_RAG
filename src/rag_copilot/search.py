from __future__ import annotations

from contextlib import closing
from pathlib import Path

from .indexing import connect, database_path
from .models import CodeChunk


def search_repository(repo_root: Path, query: str, limit: int = 5) -> list[CodeChunk]:
    if not database_path(repo_root).exists():
        raise FileNotFoundError("No index found. Run `rag-copilot index <repo>` first.")

    # OR lets natural-language queries remain useful even when not every word exists in code.
    fts_query = " OR ".join(token for token in query.split() if token.isalnum() or "_" in token)
    if not fts_query:
        return []

    with closing(connect(repo_root)) as connection:
        rows = connection.execute(
            """SELECT c.path, c.symbol, c.kind, c.start_line, c.end_line, c.code
            FROM chunks_fts f JOIN chunks c ON c.id = f.rowid
            WHERE chunks_fts MATCH ?
            ORDER BY bm25(chunks_fts, 8.0, 2.0, 1.0)
            LIMIT ?""",
            (fts_query, limit),
        ).fetchall()
    return [CodeChunk(*row) for row in rows]
