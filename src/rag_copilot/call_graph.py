from __future__ import annotations

import ast
import sqlite3

from .models import CodeChunk


def extract_call_names(source: str) -> set[str]:
    """Return direct, unqualified calls in a chunk of valid Python source."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    visitor = _DirectCallVisitor()
    visitor.visit(tree)
    return visitor.call_names


def record_call_edges(
    connection: sqlite3.Connection, indexed_chunks: list[tuple[int, CodeChunk]]
) -> None:
    """Resolve calls to symbols indexed in the same repository.

    Calls made through objects (for example ``client.fetch()``) are deliberately
    left unresolved until language-server based resolution is added.
    """
    definitions: dict[str, list[int]] = {}
    for chunk_id, chunk in indexed_chunks:
        definitions.setdefault(chunk.symbol, []).append(chunk_id)

    for caller_id, chunk in indexed_chunks:
        for call_name in extract_call_names(chunk.code):
            for callee_id in definitions.get(call_name, []):
                connection.execute(
                    """INSERT OR IGNORE INTO call_edges(caller_chunk_id, callee_chunk_id, call_name)
                    VALUES (?, ?, ?)""",
                    (caller_id, callee_id, call_name),
                )


class _DirectCallVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.call_names: set[str] = set()
        self._function_depth = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if self._function_depth:
            return
        self._function_depth += 1
        self.generic_visit(node)
        self._function_depth -= 1

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            self.call_names.add(node.func.id)
        self.generic_visit(node)
