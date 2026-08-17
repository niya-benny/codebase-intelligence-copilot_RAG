from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path

from .embeddings import HashEmbeddingProvider, cosine_similarity
from .indexing import connect, database_path
from .models import CodeChunk

RRF_K = 60


def search_repository(repo_root: Path, query: str, limit: int = 5) -> list[CodeChunk]:
    """Run FTS5 and vector retrieval, then combine rankings with RRF."""
    if not database_path(repo_root).exists():
        raise FileNotFoundError("No index found. Run `rag-copilot index <repo>` first.")

    keyword_query = _fts_query(query)
    if not keyword_query or not query.strip():
        return []

    with closing(connect(repo_root)) as connection:
        keyword_results = _keyword_search(connection, keyword_query, limit=50)
        semantic_results = _vector_search(connection, query, limit=50)

    chunks_by_id = {chunk_id: chunk for chunk_id, chunk in keyword_results + semantic_results}
    fused_ids = _reciprocal_rank_fusion(
        [[chunk_id for chunk_id, _ in keyword_results], [chunk_id for chunk_id, _ in semantic_results]]
    )
    return [chunks_by_id[chunk_id] for chunk_id in fused_ids[:limit]]


def _keyword_search(connection, query: str, limit: int) -> list[tuple[int, CodeChunk]]:
    rows = connection.execute(
        """SELECT c.id, c.path, c.symbol, c.kind, c.start_line, c.end_line, c.code
            FROM chunks_fts f JOIN chunks c ON c.id = f.rowid
            WHERE chunks_fts MATCH ?
            ORDER BY bm25(chunks_fts, 8.0, 2.0, 1.0)
            LIMIT ?""",
        (query, limit),
    ).fetchall()
    return [(row[0], CodeChunk(*row[1:])) for row in rows]


def _vector_search(connection, query: str, limit: int) -> list[tuple[int, CodeChunk]]:
    query_vector = HashEmbeddingProvider().embed(query)
    rows = connection.execute(
        """SELECT c.id, c.path, c.symbol, c.kind, c.start_line, c.end_line, c.code, e.vector
        FROM chunks c JOIN chunk_embeddings e ON e.chunk_id = c.id"""
    ).fetchall()
    scored = [
        (cosine_similarity(query_vector, json.loads(row[7])), row[0], CodeChunk(*row[1:7]))
        for row in rows
    ]
    scored.sort(key=lambda result: result[0], reverse=True)
    return [(chunk_id, chunk) for _, chunk_id, chunk in scored[:limit]]


def _fts_query(query: str) -> str:
    # OR supports natural-language queries while quoted terms avoid FTS operators.
    terms = [term for term in query.replace("_", " ").split() if term.isalnum()]
    return " OR ".join(f'"{term}"' for term in terms)


def _reciprocal_rank_fusion(rankings: list[list[int]], k: int = RRF_K) -> list[int]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (k + rank)
    return [chunk_id for chunk_id, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)]
