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


def chunk_javascript_file(repo_root: Path, file_path: Path) -> list[CodeChunk]:
    """Create Tree-sitter chunks for JavaScript functions, classes, and exports."""
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_javascript as javascript
    except ImportError as error:  # pragma: no cover - packaging guard
        raise RuntimeError("JavaScript parsing requires the project's Tree-sitter dependencies.") from error

    source = file_path.read_text(encoding="utf-8", errors="replace")
    source_bytes = source.encode("utf-8")
    parser = Parser(Language(javascript.language()))
    tree = parser.parse(source_bytes)
    relative_path = file_path.relative_to(repo_root).as_posix()
    chunks: list[CodeChunk] = []

    for node in _top_level_javascript_nodes(tree.root_node):
        chunk = _javascript_chunk(relative_path, source_bytes, node)
        if chunk:
            chunks.append(chunk)

    if not chunks and source.strip():
        line_count = len(source.splitlines())
        chunks.append(CodeChunk(relative_path, file_path.stem, "module", 1, line_count, source))
    return chunks


def chunk_source_file(repo_root: Path, file_path: Path) -> list[CodeChunk]:
    if file_path.suffix == ".py":
        return chunk_python_file(repo_root, file_path)
    return chunk_javascript_file(repo_root, file_path)


def _top_level_javascript_nodes(root):
    for child in root.named_children:
        if child.type == "export_statement":
            yield from child.named_children
        else:
            yield child


def _javascript_chunk(relative_path: str, source: bytes, node) -> CodeChunk | None:
    if node.type in {"function_declaration", "class_declaration"}:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None
        kind = "class" if node.type == "class_declaration" else "function"
        return _make_javascript_chunk(relative_path, source, node, _node_text(source, name_node), kind)

    if node.type != "lexical_declaration":
        return None
    declarator = next((child for child in node.named_children if child.type == "variable_declarator"), None)
    if not declarator:
        return None
    value = declarator.child_by_field_name("value")
    name = declarator.child_by_field_name("name")
    if not value or not name or value.type not in {"arrow_function", "function_expression"}:
        return None
    return _make_javascript_chunk(relative_path, source, node, _node_text(source, name), "function")


def _make_javascript_chunk(relative_path: str, source: bytes, node, symbol: str, kind: str) -> CodeChunk:
    return CodeChunk(
        path=relative_path,
        symbol=symbol,
        kind=kind,
        start_line=node.start_point.row + 1,
        end_line=node.end_point.row + 1,
        code=_node_text(source, node),
    )


def _node_text(source: bytes, node) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
