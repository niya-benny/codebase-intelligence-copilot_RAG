from __future__ import annotations

import argparse
from pathlib import Path

from .indexing import index_repository
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
    args = parser.parse_args()

    repository = args.repository.resolve()
    if not repository.is_dir():
        parser.error(f"Not a directory: {repository}")

    if args.command == "index":
        files, chunks = index_repository(repository)
        print(f"Indexed {chunks} chunks from {files} Python files in {repository}")
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


if __name__ == "__main__":
    main()
