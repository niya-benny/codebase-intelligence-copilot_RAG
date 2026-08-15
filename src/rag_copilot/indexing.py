from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from .chunking import chunk_python_file
from .models import CodeChunk

INDEX_DIRECTORY = ".rag-copilot"
DATABASE_NAME = "index.sqlite3"
IGNORED_DIRECTORIES = {".git", ".venv", "venv", "__pycache__", "node_modules", INDEX_DIRECTORY}


def database_path(repo_root: Path) -> Path:
    return repo_root / INDEX_DIRECTORY / DATABASE_NAME


def connect(repo_root: Path) -> sqlite3.Connection:
    db_path = database_path(repo_root)
    db_path.parent.mkdir(exist_ok=True)
    return sqlite3.connect(db_path)


def initialise_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        DROP TABLE IF EXISTS chunks;
        DROP TABLE IF EXISTS chunks_fts;
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL,
            symbol TEXT NOT NULL,
            kind TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            code TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            symbol, path, code, content='chunks', content_rowid='id'
        );
        """
    )


def iter_python_files(repo_root: Path):
    for path in repo_root.rglob("*.py"):
        if any(part in IGNORED_DIRECTORIES for part in path.relative_to(repo_root).parts):
            continue
        yield path


def index_repository(repo_root: Path) -> tuple[int, int]:
    """Rebuild the local index and return `(file_count, chunk_count)`."""
    file_count = chunk_count = 0
    # sqlite's context manager commits/rolls back but does not close the database.
    # Explicit closing is required on Windows so an index can be replaced or removed.
    with closing(connect(repo_root)) as connection, connection:
        initialise_schema(connection)
        for file_path in iter_python_files(repo_root):
            file_count += 1
            for chunk in chunk_python_file(repo_root, file_path):
                _insert_chunk(connection, chunk)
                chunk_count += 1
        connection.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
    return file_count, chunk_count


def _insert_chunk(connection: sqlite3.Connection, chunk: CodeChunk) -> None:
    connection.execute(
        """INSERT INTO chunks(path, symbol, kind, start_line, end_line, code)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (chunk.path, chunk.symbol, chunk.kind, chunk.start_line, chunk.end_line, chunk.code),
    )
