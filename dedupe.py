#!/usr/bin/env python3
"""Remove duplicate lines from text input while preserving first-seen order.

Examples:
  python dedupe.py input.txt
  cat input.txt | python dedupe.py
  python dedupe.py input.txt -o unique.txt --ignore-case --strip-whitespace
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, TextIO


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Remove duplicate lines from one or more text files or stdin.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Input files. If omitted, read from stdin.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write output to a file instead of stdout.",
    )
    parser.add_argument(
        "--ignore-case",
        action="store_true",
        help="Treat lines as duplicates regardless of case.",
    )
    parser.add_argument(
        "--strip-whitespace",
        action="store_true",
        help="Ignore leading and trailing whitespace when comparing lines.",
    )
    parser.add_argument(
        "--keep-empty",
        action="store_true",
        help="Keep the first empty line instead of dropping empty lines.",
    )
    return parser


def normalize_line(line: str, ignore_case: bool, strip_whitespace: bool) -> str:
    if strip_whitespace:
        line = line.strip()
    if ignore_case:
        line = line.casefold()
    return line


def read_lines(paths: list[Path]) -> Iterable[str]:
    if not paths:
        yield from sys.stdin
        return

    for path in paths:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            yield from handle


def dedupe_lines(
    lines: Iterable[str],
    *,
    ignore_case: bool = False,
    strip_whitespace: bool = False,
    keep_empty: bool = False,
) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []

    for raw_line in lines:
        line = raw_line.rstrip("\n")
        key = normalize_line(line, ignore_case, strip_whitespace)

        if not line and not keep_empty:
            continue

        if key in seen:
            continue

        seen.add(key)
        output.append(line)

    return output


def write_output(lines: list[str], handle: TextIO) -> None:
    if not lines:
        return
    handle.write("\n".join(lines))
    handle.write("\n")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    unique_lines = dedupe_lines(
        read_lines(args.files),
        ignore_case=args.ignore_case,
        strip_whitespace=args.strip_whitespace,
        keep_empty=args.keep_empty,
    )

    if args.output:
        with args.output.open("w", encoding="utf-8", newline="\n") as handle:
            write_output(unique_lines, handle)
    else:
        write_output(unique_lines, sys.stdout)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
