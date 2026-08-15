from pathlib import Path
import tempfile
import unittest

from rag_copilot.indexing import index_repository
from rag_copilot.search import search_repository


class SearchTests(unittest.TestCase):
    def test_search_finds_symbol(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "auth.py").write_text("def refresh_token():\n    return 'new-token'\n")
            index_repository(root)

            results = search_repository(root, "refresh_token")

            self.assertEqual(results[0].symbol, "refresh_token")
            self.assertEqual(results[0].citation, "auth.py:1-2")
