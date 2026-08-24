from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from .indexing import connect, database_path
from .models import CodeChunk


@dataclass(frozen=True)
class SymbolTrace:
    symbol: str
    definitions: list[CodeChunk]
    callers: list[CodeChunk]
    callees: list[CodeChunk]


def trace_symbol(repo_root: Path, symbol: str) -> SymbolTrace:
    """Find indexed definitions plus their local direct callers and callees."""
    if not database_path(repo_root).exists():
        raise FileNotFoundError("No index found. Run `rag-copilot index <repo>` first.")

    with closing(connect(repo_root)) as connection:
        definitions = _select_chunks(connection, "WHERE symbol = ?", (symbol,))
        definition_ids = _select_ids(connection, symbol)
        callers = _neighbours(connection, "caller_chunk_id", "callee_chunk_id", definition_ids)
        callees = _neighbours(connection, "callee_chunk_id", "caller_chunk_id", definition_ids)
    return SymbolTrace(symbol=symbol, definitions=definitions, callers=callers, callees=callees)


def _select_ids(connection, symbol: str) -> list[int]:
    rows = connection.execute("SELECT id FROM chunks WHERE symbol = ?", (symbol,)).fetchall()
    return [row[0] for row in rows]


def _select_chunks(connection, where: str, parameters: tuple) -> list[CodeChunk]:
    rows = connection.execute(
        f"""SELECT path, symbol, kind, start_line, end_line, code FROM chunks {where}
        ORDER BY path, start_line""",
        parameters,
    ).fetchall()
    return [CodeChunk(*row) for row in rows]


def _neighbours(connection, select_column: str, match_column: str, chunk_ids: list[int]) -> list[CodeChunk]:
    if not chunk_ids:
        return []
    placeholders = ", ".join("?" for _ in chunk_ids)
    rows = connection.execute(
        f"""SELECT DISTINCT c.path, c.symbol, c.kind, c.start_line, c.end_line, c.code
        FROM call_edges e JOIN chunks c ON c.id = e.{select_column}
        WHERE e.{match_column} IN ({placeholders})
        ORDER BY c.path, c.start_line""",
        chunk_ids,
    ).fetchall()
    return [CodeChunk(*row) for row in rows]
