# ekrana yazdirma ve json
from __future__ import annotations

import json
import sys
from pathlib import Path

from .replacer import ReplaceChange, ReplaceResult
from .searcher import Match, SearchResult

COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "cyan": "\033[36m",
}


def _supports_color() -> bool:
    return sys.stdout.isatty() and sys.platform != "win32" or (
        sys.platform == "win32" and "WT_SESSION" in __import__("os").environ
    )


def _c(text: str, color: str, enabled: bool) -> str:
    if not enabled:
        return text
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"


def format_search_text(
    result: SearchResult,
    *,
    pattern: str,
    line_numbers: bool = True,
    color: bool = True,
    files_only: bool = False,
    count_only: bool = False,
    with_heading: bool = True,
) -> str:
    use_color = color and _supports_color()
    lines: list[str] = []

    if count_only:
        for path in sorted({m.file for m in result.matches}):
            cnt = sum(1 for m in result.matches if m.file == path)
            lines.append(f"{path}:{cnt}")
        return "\n".join(lines)

    if files_only:
        return "\n".join(sorted({m.file for m in result.matches}))

    current_file = ""
    for match in result.matches:
        if with_heading and match.file != current_file:
            current_file = match.file
            lines.append(
                _c(current_file, "cyan", use_color)
            )

        prefix = ""
        if match.match_text in {"-", "+", ":"}:
            prefix = match.match_text
        elif line_numbers:
            sep = _c(":", "green", use_color)
            prefix = f"{match.line_no}{sep}"

        body = match.line
        if pattern and match.match_text not in {"-", "+", ":"}:
            idx = body.lower().find(match.match_text.lower()) if body else -1
            if idx >= 0:
                before = body[:idx]
                hit = body[idx : idx + len(match.match_text)]
                after = body[idx + len(match.match_text) :]
                body = (
                    before
                    + _c(hit, "red", use_color)
                    + after
                )

        lines.append(f"{prefix}{body}")

    return "\n".join(lines)


def format_search_json(result: SearchResult, pattern: str) -> str:
    payload = {
        "tool": "turkgrep",
        "pattern": pattern,
        "matches": [
            {
                "file": m.file,
                "line_number": m.line_no,
                "column": m.column,
                "line": m.line,
                "match": m.match_text,
            }
            for m in result.matches
            if m.match_text not in {"-", "+", ":"}
        ],
        "stats": {
            "files_scanned": result.stats.files_scanned,
            "files_matched": result.stats.files_matched,
            "match_count": result.stats.matches,
            "bytes_scanned": result.stats.bytes_scanned,
            "elapsed_ms": round(result.stats.elapsed_ms, 2),
            "skipped_binary": result.stats.skipped_binary,
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def format_replace_text(
    result: ReplaceResult,
    *,
    dry_run: bool = False,
    color: bool = True,
) -> str:
    use_color = color and _supports_color()
    lines: list[str] = []
    mode = "onizleme" if dry_run else "degistirildi"
    lines.append(_c(f"=== {mode} ===", "bold", use_color))

    current = ""
    for change in result.changes:
        if change.file != current:
            current = change.file
            lines.append(_c(current, "cyan", use_color))
        lines.append(
            f"{change.line_no}: "
            + _c(change.old_line, "red", use_color)
            + " -> "
            + _c(change.new_line, "green", use_color)
        )

    lines.append("")
    lines.append(
        f"{result.stats.matches} satır, "
        f"{result.stats.files_matched} dosya, "
        f"{result.stats.elapsed_ms:.1f} ms"
    )
    return "\n".join(lines)


def format_replace_json(result: ReplaceResult, pattern: str, replacement: str, *, dry_run: bool) -> str:
    payload = {
        "tool": "turkgrep",
        "mode": "replace_preview" if dry_run else "replace",
        "pattern": pattern,
        "replacement": replacement,
        "changes": [
            {
                "file": c.file,
                "line_number": c.line_no,
                "old_line": c.old_line,
                "new_line": c.new_line,
            }
            for c in result.changes
        ],
        "stats": {
            "files_scanned": result.stats.files_scanned,
            "files_changed": result.stats.files_matched,
            "lines_changed": result.stats.matches,
            "bytes_scanned": result.stats.bytes_scanned,
            "elapsed_ms": round(result.stats.elapsed_ms, 2),
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
