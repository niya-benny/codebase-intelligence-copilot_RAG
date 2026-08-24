# Codebase Intelligence Copilot

A local-first RAG assistant for unfamiliar codebases. It indexes source code into
structure-aware chunks and retrieves evidence with file-and-line citations.

## Milestone 1

This initial version supports Python and JavaScript repositories and provides:

- AST-aware chunks for modules, classes, and functions
- Tree-sitter JavaScript chunks for functions, classes, and exported declarations
- SQLite FTS5 keyword search
- Local dense-vector similarity fused with keyword results using reciprocal-rank fusion
- Query rewriting and code-aware reranking that prioritize symbol and path evidence
- A CLI that returns grounded code excerpts with `path:start-end` citations

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .

# Index another repository (the index is stored in .rag-copilot/ there)
rag-copilot index C:\path\to\repository
rag-copilot search C:\path\to\repository "where is token refresh handled?"
rag-copilot trace C:\path\to\repository refresh_token
```

## Roadmap

1. **Now:** reliable local keyword retrieval and citation-ready Python chunks.
2. Swap the local vector baseline and deterministic reranker for code-trained models.
3. Add TypeScript and more Tree-sitter languages; resolve object/import calls in the graph.
4. Add answer generation, evaluation data, incremental Git indexing, and a web UI.

## Project layout

```text
src/rag_copilot/   CLI, indexing, chunking, and search
tests/              automated checks
```
