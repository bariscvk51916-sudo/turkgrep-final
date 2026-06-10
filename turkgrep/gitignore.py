# gitignore okuma (tam rg kadar degil ama is goruyor)
from __future__ import annotations

import os
from pathlib import Path


def _match_segment(pattern: str, name: str) -> bool:
    if pattern == name:
        return True
    if pattern.startswith("*") and pattern.endswith("*"):
        return pattern[1:-1] in name
    if pattern.startswith("*"):
        return name.endswith(pattern[1:])
    if pattern.endswith("*"):
        return name.startswith(pattern[:-1])
    return False


def _match_path(pattern: str, rel_path: str) -> bool:
    parts = rel_path.replace("\\", "/").split("/")
    pat_parts = pattern.replace("\\", "/").split("/")

    if len(pat_parts) == 1:
        return any(_match_segment(pat_parts[0], p) for p in parts)

    if len(pat_parts) != len(parts):
        if pat_parts[-1].startswith("*") and len(parts) >= len(pat_parts) - 1:
            prefix = pat_parts[:-1]
            if len(parts) < len(prefix):
                return False
            for p, n in zip(prefix, parts):
                if p != n and not _match_segment(p, n):
                    return False
            return _match_segment(pat_parts[-1], parts[-1])
        return False

    return all(
        p == n or _match_segment(p, n) for p, n in zip(pat_parts, parts)
    )


class GitignoreMatcher:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self._rules: list[tuple[bool, str]] = []
        self._load_rules()

    def _load_rules(self) -> None:
        gitignore = self.root / ".gitignore"
        if not gitignore.is_file():
            return
        for line in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            negate = line.startswith("!")
            if negate:
                line = line[1:]
            self._rules.append((negate, line))

    def is_ignored(self, path: Path) -> bool:
        try:
            rel = path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return False

        ignored = False
        for negate, pattern in self._rules:
            if _match_path(pattern, rel) or _match_path(pattern, path.name):
                ignored = not negate if negate else True
        return ignored


def should_skip_dir(name: str) -> bool:
    return name in {
        ".git",
        ".svn",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        ".turkgrep_cache",
    }
