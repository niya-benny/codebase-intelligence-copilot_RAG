from pathlib import Path
import tempfile
import unittest

from rag_copilot.chunking import chunk_python_file
from rag_copilot.chunking import chunk_javascript_file


class ChunkingTests(unittest.TestCase):
    def test_chunks_top_level_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "example.py"
            source.write_text("def greet(name):\n    return f'Hi {name}'\n\nclass User:\n    pass\n")

            chunks = chunk_python_file(root, source)

            self.assertEqual(
                [(chunk.symbol, chunk.start_line, chunk.end_line) for chunk in chunks],
                [("greet", 1, 2), ("User", 4, 5)],
            )

    def test_chunks_javascript_exports_and_arrow_functions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "auth.js"
            source.write_text(
                "export function refreshToken() {\n  return 'new-token';\n}\n\n"
                "const getToken = () => refreshToken();\n"
            )

            chunks = chunk_javascript_file(root, source)

            self.assertEqual([(chunk.symbol, chunk.kind) for chunk in chunks], [
                ("refreshToken", "function"),
                ("getToken", "function"),
            ])
