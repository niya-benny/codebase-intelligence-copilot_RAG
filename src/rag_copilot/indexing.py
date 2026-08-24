from __future__ import annotations

import sqlite3
from contextlib import closing
import json
from pathlib import Path

from .chunking import chunk_source_file
from .call_graph import record_call_edges
from .embeddings import HashEmbeddingProvider
from .models import CodeChunk

INDEX_DIRECTORY = ".rag-copilot"
DATABASE_NAME = "index.sqlite3"
IGNORED_DIRECTORIES = {".git", ".venv", "venv", "__pycache__", "node_modules", INDEX_DIRECTORY}
SOURCE_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".jsx"}


def database_path(repo_root: Path) -> Path:
    return repo_root / INDEX_DIRECTORY / DATABASE_NAME


def connect(repo_root: Path) -> sqlite3.Connection:
    db_path = database_path(repo_root)
    db_path.parent.mkdir(exist_ok=True)
    return sqlite3.connect(db_path)


def initialise_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        DROP TABLE IF EXISTS call_edges;
        DROP TABLE IF EXISTS chunk_embeddings;
        DROP TABLE IF EXISTS chunks_fts;
        DROP TABLE IF EXISTS chunks;
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
        CREATE TABLE chunk_embeddings (
            chunk_id INTEGER PRIMARY KEY REFERENCES chunks(id),
            vector TEXT NOT NULL
        );
        CREATE TABLE call_edges (
            caller_chunk_id INTEGER NOT NULL REFERENCES chunks(id),
            callee_chunk_id INTEGER NOT NULL REFERENCES chunks(id),
            call_name TEXT NOT NULL,
            UNIQUE(caller_chunk_id, callee_chunk_id, call_name)
        );
        """
    )


def iter_source_files(repo_root: Path):
    for path in repo_root.rglob("*"):
        if path.suffix not in SOURCE_SUFFIXES:
            continue
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
        embedder = HashEmbeddingProvider()
        indexed_chunks: list[tuple[int, CodeChunk]] = []
        for file_path in iter_source_files(repo_root):
            file_count += 1
            for chunk in chunk_source_file(repo_root, file_path):
                indexed_chunks.append((_insert_chunk(connection, chunk, embedder), chunk))
                chunk_count += 1
        record_call_edges(connection, indexed_chunks)
        connection.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
    return file_count, chunk_count


def _insert_chunk(
    connection: sqlite3.Connection, chunk: CodeChunk, embedder: HashEmbeddingProvider
) -> int:
    cursor = connection.execute(
        """INSERT INTO chunks(path, symbol, kind, start_line, end_line, code)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (chunk.path, chunk.symbol, chunk.kind, chunk.start_line, chunk.end_line, chunk.code),
    )
    embedding_text = f"{chunk.symbol}\n{chunk.kind}\n{chunk.path}\n{chunk.code}"
    connection.execute(
        "INSERT INTO chunk_embeddings(chunk_id, vector) VALUES (?, ?)",
        (cursor.lastrowid, json.dumps(embedder.embed(embedding_text))),
    )
    return cursor.lastrowid
