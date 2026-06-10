# dosya arama - thread ile paralel okuyor
from __future__ import annotations

import mmap
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

from .gitignore import GitignoreMatcher, should_skip_dir

BINARY_CHECK_BYTES = 8192
MMAP_THRESHOLD = 256 * 1024  # kucuk dosyada mmap yavaslatiyor
TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".cs", ".go", ".rs",
    ".txt", ".md", ".json", ".xml", ".html", ".css", ".sql", ".yaml", ".yml",
}
DEFAULT_WORKERS = max(4, (os.cpu_count() or 4) * 4)
BATCH_SIZE = 16


@dataclass
class Match:
    file: str
    line_no: int
    line: str
    column: int = 1
    match_text: str = ""


@dataclass
class SearchStats:
    files_scanned: int = 0
    files_matched: int = 0
    matches: int = 0
    bytes_scanned: int = 0
    elapsed_ms: float = 0.0
    skipped_binary: int = 0


@dataclass
class SearchResult:
    matches: list[Match] = field(default_factory=list)
    stats: SearchStats = field(default_factory=SearchStats)


def is_binary_file(path: Path) -> bool:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return False
    try:
        with path.open("rb") as f:
            chunk = f.read(BINARY_CHECK_BYTES)
        return b"\x00" in chunk
    except OSError:
        return True


def _read_text(path: Path, size: int) -> str:
    if size < MMAP_THRESHOLD:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1", errors="replace")

    with path.open("rb") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            try:
                return mm.read().decode("utf-8")
            except UnicodeDecodeError:
                return mm.read().decode("latin-1", errors="replace")


def iter_files(
    paths: list[Path],
    *,
    hidden: bool = False,
    respect_gitignore: bool = True,
    extensions: set[str] | None = None,
) -> Iterator[Path]:
    for raw in paths:
        path = raw.resolve()
        if path.is_file():
            if extensions and path.suffix.lstrip(".") not in extensions:
                continue
            yield path
            continue

        if not path.is_dir():
            continue

        matcher = GitignoreMatcher(path) if respect_gitignore else None

        for root, dirs, files in os.walk(path):
            root_path = Path(root)
            dirs[:] = [
                d
                for d in sorted(dirs)
                if (hidden or not d.startswith("."))
                and not should_skip_dir(d)
                and (
                    matcher is None
                    or not matcher.is_ignored(root_path / d)
                )
            ]

            for name in sorted(files):
                if not hidden and name.startswith("."):
                    continue
                file_path = root_path / name
                if extensions and file_path.suffix.lstrip(".") not in extensions:
                    continue
                if matcher and matcher.is_ignored(file_path):
                    continue
                yield file_path


def _search_file(
    path: Path,
    pattern: re.Pattern[str],
    *,
    before: int = 0,
    after: int = 0,
) -> tuple[list[Match], int, bool, bool]:
    matches: list[Match] = []
    size = 0
    if is_binary_file(path):
        return matches, size, False, True

    try:
        size = path.stat().st_size
        if size == 0:
            return matches, 0, False, False

        text = _read_text(path, size)
        lines = text.splitlines()
        hit_indices: list[int] = []

        for i, line in enumerate(lines, start=1):
            m = pattern.search(line)
            if m:
                hit_indices.append(i)
                matches.append(
                    Match(
                        file=str(path),
                        line_no=i,
                        line=line,
                        column=m.start() + 1,
                        match_text=m.group(0),
                    )
                )

        if before or after:
            context_matches: list[Match] = []
            shown: set[tuple[str, int]] = set()
            for idx in hit_indices:
                start = max(1, idx - before)
                end = min(len(lines), idx + after)
                for ln in range(start, end + 1):
                    key = (str(path), ln)
                    if key in shown:
                        continue
                    shown.add(key)
                    prefix = ""
                    if ln < idx:
                        prefix = "-"
                    elif ln > idx:
                        prefix = "+"
                    elif before or after:
                        prefix = ":"
                    context_matches.append(
                        Match(
                            file=str(path),
                            line_no=ln,
                            line=lines[ln - 1],
                            column=1,
                            match_text=prefix,
                        )
                    )
            return context_matches, size, bool(hit_indices), False

        return matches, size, bool(hit_indices), False
    except OSError:
        return [], 0, False, False


class Searcher:
    def __init__(
        self,
        pattern: str,
        *,
        ignore_case: bool = False,
        fixed_strings: bool = False,
        word_regexp: bool = False,
        workers: int = DEFAULT_WORKERS,
    ) -> None:
        flags = re.MULTILINE
        if ignore_case:
            flags |= re.IGNORECASE

        if fixed_strings:
            expr = re.escape(pattern)
        else:
            expr = pattern

        if word_regexp:
            expr = rf"\b{expr}\b"

        self.pattern = re.compile(expr, flags)
        self.workers = workers

    def search(
        self,
        paths: list[Path],
        *,
        hidden: bool = False,
        respect_gitignore: bool = True,
        extensions: set[str] | None = None,
        before: int = 0,
        after: int = 0,
        max_results: int | None = None,
        progress: Callable[[int], None] | None = None,
    ) -> SearchResult:
        files = list(
            iter_files(
                paths,
                hidden=hidden,
                respect_gitignore=respect_gitignore,
                extensions=extensions,
            )
        )

        start = time.perf_counter()
        all_matches: list[Match] = []
        stats = SearchStats()

        def task_batch(batch: list[Path]) -> list[tuple[list[Match], int, bool, bool]]:
            return [
                _search_file(fp, self.pattern, before=before, after=after)
                for fp in batch
            ]

        batches = [
            files[i : i + BATCH_SIZE]
            for i in range(0, len(files), BATCH_SIZE)
        ]

        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {pool.submit(task_batch, batch): batch for batch in batches}
            done = 0
            for future in as_completed(futures):
                done += len(futures[future])
                if progress:
                    progress(done)
                for ms, size, matched, binary in future.result():
                    stats.files_scanned += 1
                    stats.bytes_scanned += size
                    if binary:
                        stats.skipped_binary += 1
                    if matched:
                        stats.files_matched += 1
                    if before or after:
                        stats.matches += len(ms)
                    else:
                        stats.matches += len(ms)
                    all_matches.extend(ms)

                    if max_results and stats.matches >= max_results:
                        break

                if max_results and stats.matches >= max_results:
                    for f in futures:
                        f.cancel()
                    break

        stats.elapsed_ms = (time.perf_counter() - start) * 1000
        all_matches.sort(key=lambda m: (m.file, m.line_no))
        return SearchResult(matches=all_matches, stats=stats)
