# bul-degistir kismi
from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from .searcher import SearchStats, is_binary_file, iter_files


@dataclass
class ReplaceChange:
    file: str
    line_no: int
    old_line: str
    new_line: str


@dataclass
class ReplaceResult:
    changes: list[ReplaceChange] = field(default_factory=list)
    stats: SearchStats = field(default_factory=SearchStats)


def _replace_in_file(
    path: Path,
    pattern: re.Pattern[str],
    replacement: str,
    *,
    count: int = 0,
) -> tuple[list[ReplaceChange], int, bool]:
    if is_binary_file(path):
        return [], 0, True

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = path.read_text(encoding="latin-1")
        except OSError:
            return [], 0, False
    except OSError:
        return [], 0, False

    lines = text.splitlines(keepends=True)
    changes: list[ReplaceChange] = []
    new_lines: list[str] = []
    modified = False
    size = len(text.encode("utf-8", errors="ignore"))

    for i, line in enumerate(lines, start=1):
        if pattern.search(line):
            new_line, n = pattern.subn(replacement, line, count=count or 0)
            if n > 0 and new_line != line:
                changes.append(
                    ReplaceChange(
                        file=str(path),
                        line_no=i,
                        old_line=line.rstrip("\r\n"),
                        new_line=new_line.rstrip("\r\n"),
                    )
                )
                modified = True
                new_lines.append(new_line)
                continue
        new_lines.append(line)

    if modified:
        path.write_text("".join(new_lines), encoding="utf-8")

    return changes, size, False


class Replacer:
    def __init__(
        self,
        pattern: str,
        replacement: str,
        *,
        ignore_case: bool = False,
        fixed_strings: bool = False,
        workers: int = 4,
    ) -> None:
        flags = re.MULTILINE
        if ignore_case:
            flags |= re.IGNORECASE
        expr = re.escape(pattern) if fixed_strings else pattern
        self.pattern = re.compile(expr, flags)
        self.replacement = replacement
        self.workers = workers

    def replace(
        self,
        paths: list[Path],
        *,
        dry_run: bool = False,
        hidden: bool = False,
        respect_gitignore: bool = True,
        extensions: set[str] | None = None,
        backup: bool = False,
    ) -> ReplaceResult:
        files = list(
            iter_files(
                paths,
                hidden=hidden,
                respect_gitignore=respect_gitignore,
                extensions=extensions,
            )
        )

        start = time.perf_counter()
        all_changes: list[ReplaceChange] = []
        stats = SearchStats()

        def task(file_path: Path) -> tuple[list[ReplaceChange], int, bool]:
            if dry_run:
                return _preview_replace(file_path, self.pattern, self.replacement)
            if backup:
                backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                backup_path.write_bytes(file_path.read_bytes())
            return _replace_in_file(file_path, self.pattern, self.replacement)

        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {pool.submit(task, fp): fp for fp in files}
            for future in as_completed(futures):
                changes, size, binary = future.result()
                stats.files_scanned += 1
                stats.bytes_scanned += size
                if binary:
                    stats.skipped_binary += 1
                if changes:
                    stats.files_matched += 1
                    stats.matches += len(changes)
                    all_changes.extend(changes)

        stats.elapsed_ms = (time.perf_counter() - start) * 1000
        all_changes.sort(key=lambda c: (c.file, c.line_no))
        return ReplaceResult(changes=all_changes, stats=stats)


def _preview_replace(
    path: Path,
    pattern: re.Pattern[str],
    replacement: str,
) -> tuple[list[ReplaceChange], int, bool]:
    if is_binary_file(path):
        return [], 0, True

    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return [], 0, False

    changes: list[ReplaceChange] = []
    size = len(text.encode("utf-8", errors="ignore"))

    for i, line in enumerate(text.splitlines(), start=1):
        if pattern.search(line):
            new_line = pattern.sub(replacement, line)
            if new_line != line:
                changes.append(
                    ReplaceChange(
                        file=str(path),
                        line_no=i,
                        old_line=line,
                        new_line=new_line,
                    )
                )

    return changes, size, False
