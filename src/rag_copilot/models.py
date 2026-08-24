from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CodeChunk:
    """A retrievable, citation-ready section of source code."""

    path: str
    symbol: str
    kind: str
    start_line: int
    end_line: int
    code: str

    @property
    def citation(self) -> str:
        return f"{self.path}:{self.start_line}-{self.end_line}"
