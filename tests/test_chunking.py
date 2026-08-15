from pathlib import Path
import tempfile
import unittest

from rag_copilot.chunking import chunk_python_file


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
