from pathlib import Path
import tempfile
import unittest

from rag_copilot.indexing import index_repository
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
