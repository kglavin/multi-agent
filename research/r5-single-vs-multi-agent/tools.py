"""The tools every R5 configuration gets: list, read, and search files under one corpus root."""

from __future__ import annotations

import re
import signal
from pathlib import Path

from harness import Tool, ToolSpec

MAX_MATCHES = 200
MAX_CHARS = 20_000  # about 5,000 tokens. The largest S3 file is 119k characters.
SEARCH_TIMEOUT_S = 30  # a regex with nested repeats can backtrack for hours, and re has no timeout


class _SearchTimeout(Exception):
    pass


def _on_alarm(*_):
    raise _SearchTimeout


def _cap(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    shown = text[:max_chars]
    lines = shown.count("\n") + 1
    return (shown + f"\n... output cut at {max_chars} characters ({lines} lines). "
            "Use start_line and end_line, or a narrower search.")


def corpus_tools(root: Path, max_chars: int = MAX_CHARS) -> list[Tool]:
    """Each tool's output is cut at max_chars so one call cannot fill the context window."""
    root = root.resolve()

    def resolve(path: str) -> Path:
        p = (root / path.lstrip("/")).resolve()  # "/" means the corpus root
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
        return _cap("\n".join(lines[start_line - 1:end_line]), max_chars)

    def find_files(pattern: str, path: str = ".") -> str:
        try:
            base = resolve(path)
            found = sorted(f for f in base.rglob(pattern) if f.is_file())
        except (ValueError, OSError) as e:
            return f"error: {e}"
        lines = [f.relative_to(root).as_posix() for f in found[:MAX_MATCHES]]
        more = f"\n... stopped at {MAX_MATCHES} files" if len(found) > MAX_MATCHES else ""
        return (_cap("\n".join(lines), max_chars) + more) if lines else "no files"

    def search(pattern: str, path: str = ".") -> str:
        try:
            regex = re.compile(pattern)
            base = resolve(path)
        except (ValueError, re.error) as e:
            return f"error: {e}"
        files = [base] if base.is_file() else sorted(f for f in base.rglob("*") if f.is_file())
        previous = signal.signal(signal.SIGALRM, _on_alarm)  # tools run in the main thread
        signal.setitimer(signal.ITIMER_REAL, SEARCH_TIMEOUT_S)
        try:
            matches = []
            for f in files:
                for n, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
                    if regex.search(line):
                        matches.append(f"{f.relative_to(root).as_posix()}:{n}: {line.strip()}")
                        if len(matches) == MAX_MATCHES:
                            return _cap("\n".join(matches), max_chars) + f"\n... stopped at {MAX_MATCHES} matches"
            return _cap("\n".join(matches), max_chars) or "no matches"
        except _SearchTimeout:
            return f"error: search stopped after {SEARCH_TIMEOUT_S} seconds. Use a simpler pattern."
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)

    path_param = {"type": "string", "description": "Path relative to the corpus root. The root is \".\"."}
    return [
        Tool(ToolSpec("list_files", "List the files and directories directly inside a directory, one level only. "
                                    "Directories end with /. Use \".\" for the corpus root.",
                      {"type": "object", "properties": {"path": path_param}}), list_files),
        Tool(ToolSpec("read_file", f"Read a text file, optionally only lines start_line to end_line inclusive. "
                                   f"Output is cut at {max_chars} characters.",
                      {"type": "object", "properties": {"path": path_param, "start_line": {"type": "integer"},
                                                        "end_line": {"type": "integer"}},
                       "required": ["path"]}), read_file),
        Tool(ToolSpec("find_files", f"Find files by name in a directory and all its subdirectories, using a "
                                    f"glob pattern such as \"apps.py\" or \"*.md\". Returns paths, at most "
                                    f"{MAX_MATCHES}.",
                      {"type": "object", "properties": {"pattern": {"type": "string"}, "path": path_param},
                       "required": ["pattern"]}), find_files),
        Tool(ToolSpec("search", f"Search the contents of files, in a directory and all its subdirectories, for "
                                f"a Python regular expression. Returns path:line: text, at most {MAX_MATCHES} "
                                f"matches. It does not match file names. Use find_files for that.",
                      {"type": "object", "properties": {"pattern": {"type": "string"}, "path": path_param},
                       "required": ["pattern"]}), search),
    ]
