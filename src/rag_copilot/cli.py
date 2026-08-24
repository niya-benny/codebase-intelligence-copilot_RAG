from __future__ import annotations

import argparse
from pathlib import Path

from .indexing import index_repository
from .graph_search import trace_symbol
from .search import search_repository


def main() -> None:
    parser = argparse.ArgumentParser(description="Search a codebase with citation-ready results.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    index_parser = subcommands.add_parser("index", help="Build a local index for a repository")
    index_parser.add_argument("repository", type=Path)
    search_parser = subcommands.add_parser("search", help="Search an indexed repository")
    search_parser.add_argument("repository", type=Path)
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=5)
    trace_parser = subcommands.add_parser("trace", help="Show local callers and callees of a symbol")
    trace_parser.add_argument("repository", type=Path)
    trace_parser.add_argument("symbol")
    args = parser.parse_args()

    repository = args.repository.resolve()
    if not repository.is_dir():
        parser.error(f"Not a directory: {repository}")

    if args.command == "index":
        files, chunks = index_repository(repository)
        print(f"Indexed {chunks} chunks from {files} source files in {repository}")
        return

    if args.command == "trace":
        try:
            trace = trace_symbol(repository, args.symbol)
        except FileNotFoundError as error:
            parser.error(str(error))
        if not trace.definitions:
            print(f"No indexed definition found for: {args.symbol}")
            return
        _print_trace_section("Definitions", trace.definitions)
        _print_trace_section("Called by", trace.callers)
        _print_trace_section("Calls", trace.callees)
        return

    try:
        results = search_repository(repository, args.query, args.limit)
    except FileNotFoundError as error:
        parser.error(str(error))
    if not results:
        print("No matching code chunks found.")
        return
    for result in results:
        print(f"\n{result.kind} {result.symbol} - {result.citation}\n{result.code}")


def _print_trace_section(title: str, chunks) -> None:
    print(f"\n{title}:")
    if not chunks:
        print("  (none found)")
        return
    for chunk in chunks:
        print(f"  {chunk.kind} {chunk.symbol} - {chunk.citation}")


if __name__ == "__main__":
    main()
