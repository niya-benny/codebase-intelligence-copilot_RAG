from pathlib import Path
import tempfile
import unittest

from rag_copilot.indexing import index_repository
from rag_copilot.models import CodeChunk
from rag_copilot.query_rewrite import rewrite_query
from rag_copilot.reranking import rerank_chunks
from rag_copilot.search import _reciprocal_rank_fusion, search_repository


class SearchTests(unittest.TestCase):
    def test_search_finds_symbol(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "auth.py").write_text("def refresh_token():\n    return 'new-token'\n")
            index_repository(root)

            results = search_repository(root, "refresh_token")

            self.assertEqual(results[0].symbol, "refresh_token")
            self.assertEqual(results[0].citation, "auth.py:1-2")

    def test_rank_fusion_rewards_results_seen_by_both_retrievers(self) -> None:
        fused = _reciprocal_rank_fusion([[10, 20], [20, 30]])

        self.assertEqual(fused[0], 20)

    def test_query_rewrite_expands_common_code_vocabulary(self) -> None:
        rewritten = rewrite_query("where is auth login handled?")

        self.assertEqual(
            rewritten.terms,
            ("auth", "authentication", "login", "authenticate", "handled"),
        )

    def test_reranker_prefers_symbol_evidence(self) -> None:
        chunks = {
            1: CodeChunk("handlers.py", "handle_request", "function", 1, 2, "return refresh token"),
            2: CodeChunk("auth.py", "refresh_token", "function", 1, 2, "return token"),
        }

        reranked = rerank_chunks([1, 2], chunks, "refresh token")

        self.assertEqual(reranked[0], 2)
