from __future__ import annotations

import re
from dataclasses import dataclass


WORD_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "does",
    "for",
    "how",
    "in",
    "is",
    "of",
    "the",
    "this",
    "to",
    "what",
    "where",
    "which",
}
EXPANSIONS = {
    "auth": ("authentication",),
    "call": ("caller", "callee", "invoke"),
    "config": ("configuration",),
    "error": ("exception", "raise"),
    "login": ("authenticate", "authentication"),
}


@dataclass(frozen=True)
class RewrittenQuery:
    original: str
    terms: tuple[str, ...]

    @property
    def text(self) -> str:
        return " ".join(self.terms)


def rewrite_query(query: str) -> RewrittenQuery:
    """Normalize identifier spelling and add a small, auditable code vocabulary."""
    terms: list[str] = []
    for token in WORD_PATTERN.findall(query):
        normalised = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", token).replace("_", " ").lower()
        for word in normalised.split():
            if word in STOP_WORDS:
                continue
            _append_unique(terms, word)
            for expansion in EXPANSIONS.get(word, ()):
                _append_unique(terms, expansion)
    return RewrittenQuery(original=query, terms=tuple(terms))


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)
