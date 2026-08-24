from __future__ import annotations

from .models import CodeChunk
from .query_rewrite import rewrite_query


def rerank_chunks(
    chunk_ids: list[int], chunks_by_id: dict[int, CodeChunk], query: str
) -> list[int]:
    """Prefer evidence in a symbol or path over incidental body-text matches.

    This deterministic baseline runs locally. It intentionally has the same input
    and output shape a cross-encoder reranker would use in a later milestone.
    """
    terms = set(rewrite_query(query).terms)
    positions = {chunk_id: position for position, chunk_id in enumerate(chunk_ids)}
    return sorted(
        chunk_ids,
        key=lambda chunk_id: (-_evidence_score(chunks_by_id[chunk_id], terms), positions[chunk_id]),
    )


def _evidence_score(chunk: CodeChunk, terms: set[str]) -> float:
    symbol_terms = set(rewrite_query(chunk.symbol).terms)
    path_terms = set(rewrite_query(chunk.path).terms)
    code_terms = set(rewrite_query(chunk.code).terms)
    return (
        4.0 * len(terms & symbol_terms)
        + 1.5 * len(terms & path_terms)
        + 0.5 * len(terms & code_terms)
    )
