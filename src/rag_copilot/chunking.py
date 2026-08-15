from __future__ import annotations

import ast
from pathlib import Path

from .models import CodeChunk


def chunk_python_file(repo_root: Path, file_path: Path) -> list[CodeChunk]:
    """Create one chunk per top-level class/function, plus a module fallback."""
    source = file_path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines()
    relative_path = file_path.relative_to(repo_root).as_posix()
    chunks: list[CodeChunk] = []

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        start = node.lineno
        end = node.end_lineno or start
        symbol_kind = "class" if isinstance(node, ast.ClassDef) else "function"
        chunks.append(
            CodeChunk(
                path=relative_path,
                symbol=node.name,
                kind=symbol_kind,
                start_line=start,
                end_line=end,
                code="\n".join(lines[start - 1 : end]),
            )
        )

    if not chunks and source.strip():
        chunks.append(
            CodeChunk(
                path=relative_path,
                symbol=file_path.stem,
                kind="module",
                start_line=1,
                end_line=len(lines),
                code=source,
            )
        )
    return chunks
