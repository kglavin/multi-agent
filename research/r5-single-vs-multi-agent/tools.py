"""The tools every R5 configuration gets: list, read, and search files under one corpus root."""

from __future__ import annotations

import re
from pathlib import Path

from harness import Tool, ToolSpec

MAX_MATCHES = 200


def corpus_tools(root: Path) -> list[Tool]:
    root = root.resolve()

    def resolve(path: str) -> Path:
        p = (root / path).resolve()
        if not p.is_relative_to(root):
            raise ValueError(f"path outside corpus: {path}")
        return p

    def list_files(path: str = ".") -> str:
        try:
            d = resolve(path)
            entries = sorted(d.iterdir())
        except (ValueError, OSError) as e:
            return f"error: {e}"
        return "\n".join(e.relative_to(root).as_posix() + ("/" if e.is_dir() else "") for e in entries)

    def read_file(path: str, start_line: int = 1, end_line: int | None = None) -> str:
        try:
            lines = resolve(path).read_text().splitlines()
        except (ValueError, OSError) as e:
            return f"error: {e}"
        return "\n".join(lines[start_line - 1:end_line])

    def search(pattern: str, path: str = ".") -> str:
        try:
            regex = re.compile(pattern)
            base = resolve(path)
        except (ValueError, re.error) as e:
            return f"error: {e}"
        files = [base] if base.is_file() else sorted(f for f in base.rglob("*") if f.is_file())
        matches = []
        for f in files:
            for n, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
                if regex.search(line):
                    matches.append(f"{f.relative_to(root).as_posix()}:{n}: {line.strip()}")
                    if len(matches) == MAX_MATCHES:
                        return "\n".join(matches) + f"\n... stopped at {MAX_MATCHES} matches"
        return "\n".join(matches) or "no matches"

    path_param = {"type": "string", "description": "Path relative to the corpus root"}
    return [
        Tool(ToolSpec("list_files", "List the files and directories in a directory. Directories end with /.",
                      {"type": "object", "properties": {"path": path_param}}), list_files),
        Tool(ToolSpec("read_file", "Read a text file, optionally only lines start_line to end_line inclusive.",
                      {"type": "object", "properties": {"path": path_param, "start_line": {"type": "integer"},
                                                        "end_line": {"type": "integer"}},
                       "required": ["path"]}), read_file),
        Tool(ToolSpec("search", f"Search files for a Python regular expression. Returns path:line: text, "
                                f"at most {MAX_MATCHES} matches.",
                      {"type": "object", "properties": {"pattern": {"type": "string"}, "path": path_param},
                       "required": ["pattern"]}), search),
    ]
