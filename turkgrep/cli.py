# komut satiri
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .output import (
    format_replace_json,
    format_replace_text,
    format_search_json,
    format_search_text,
)
from .replacer import Replacer
from .searcher import Searcher


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tg",
        description="Dosyalarda arama ve degistirme araci (final odevi)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  tg "def main" src/
  tg -i "TODO" --type py
  tg -n -C 2 "import" .
  tg --json "class" tests/
  tg "old_name" -r "new_name" src/ --dry-run
  tg "foo" -r "bar" file.py --backup
  tg --benchmark "import" .
        """,
    )

    parser.add_argument("pattern", nargs="?", help="Aranacak desen (regex veya düz metin)")
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="Aranacak dosya veya dizinler (varsayılan: .)",
    )
    parser.add_argument("-V", "--version", action="version", version=f"turkgrep {__version__}")

    # Arama seçenekleri
    search = parser.add_argument_group("Arama")
    search.add_argument("-i", "--ignore-case", action="store_true", help="Büyük/küçük harf duyarsız")
    search.add_argument("-F", "--fixed-strings", action="store_true", help="Regex yerine düz metin ara")
    search.add_argument("-w", "--word-regexp", action="store_true", help="Tam kelime eşleşmesi")
    search.add_argument("-n", "--line-number", action="store_true", help="Satır numarası göster")
    search.add_argument("-l", "--files-with-matches", action="store_true", help="Sadece eşleşen dosyaları listele")
    search.add_argument("-c", "--count", action="store_true", help="Dosya başına eşleşme sayısı")
    search.add_argument("-C", "--context", type=int, metavar="N", help="Eşleşme öncesi/sonrası N satır")
    search.add_argument("--hidden", action="store_true", help="Gizli dosyaları da tara")
    search.add_argument("--no-ignore", action="store_true", help=".gitignore kurallarını yok say")
    search.add_argument(
        "--type",
        dest="file_type",
        metavar="EXT",
        help="Dosya uzantısı filtresi (ör: py, js, java)",
    )
    search.add_argument("--max-count", type=int, metavar="N", help="En fazla N sonuç")
    search.add_argument("--no-color", action="store_true", help="Renkli çıktıyı kapat")

    # Çıktı
    output = parser.add_argument_group("Çıktı")
    output.add_argument("--json", action="store_true", help="JSON formatinda cikti")
    output.add_argument("-q", "--quiet", action="store_true", help="Sadece hata mesajları")

    # Değiştirme
    replace = parser.add_argument_group("Değiştirme")
    replace.add_argument("-r", "--replace", metavar="YENİ", help="Eşleşmeleri YENİ değerle değiştir")
    replace.add_argument("--dry-run", action="store_true", help="Değişiklikleri uygulamadan önizle")
    replace.add_argument("--backup", action="store_true", help="Değiştirmeden önce .bak yedeği al")
    replace.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=0,
        metavar="N",
        help="Paralel iş parçacığı sayısı (varsayılan: CPU x2)",
    )

    # Diğer
    parser.add_argument("--benchmark", action="store_true", help="Performans ölçümü yap ve çık")
    parser.add_argument("--gui", action="store_true", help="Arayuzu ac")

    return parser


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.gui:
        from .gui import main as gui_main

        gui_main()
        return 0

    if args.benchmark:
        if not args.pattern:
            parser.error("--benchmark için desen gerekli")
        return _run_benchmark(args)

    if not args.pattern:
        parser.error("Arama deseni gerekli")

    paths = [Path(p) for p in args.paths]
    extensions = {args.file_type.lstrip(".")} if args.file_type else None
    workers = args.jobs if args.jobs > 0 else None

    if args.replace is not None:
        replacer = Replacer(
            args.pattern,
            args.replace,
            ignore_case=args.ignore_case,
            fixed_strings=args.fixed_strings,
            workers=workers or 4,
        )
        result = replacer.replace(
            paths,
            dry_run=args.dry_run,
            hidden=args.hidden,
            respect_gitignore=not args.no_ignore,
            extensions=extensions,
            backup=args.backup and not args.dry_run,
        )

        if args.json:
            print(
                format_replace_json(
                    result,
                    args.pattern,
                    args.replace,
                    dry_run=args.dry_run,
                )
            )
        elif not args.quiet:
            print(
                format_replace_text(
                    result,
                    dry_run=args.dry_run,
                    color=not args.no_color,
                )
            )
        return 0 if result.changes or args.dry_run else 1

    searcher_kwargs = {
        "ignore_case": args.ignore_case,
        "fixed_strings": args.fixed_strings,
        "word_regexp": args.word_regexp,
    }
    if workers:
        searcher_kwargs["workers"] = workers

    searcher = Searcher(args.pattern, **searcher_kwargs)
    before = after = 0
    if args.context:
        before = after = args.context

    result = searcher.search(
        paths,
        hidden=args.hidden,
        respect_gitignore=not args.no_ignore,
        extensions=extensions,
        before=before,
        after=after,
        max_results=args.max_count,
    )

    if args.json:
        print(format_search_json(result, args.pattern))
    elif not args.quiet:
        print(
            format_search_text(
                result,
                pattern=args.pattern,
                line_numbers=args.line_number or args.context is not None,
                color=not args.no_color,
                files_only=args.files_with_matches,
                count_only=args.count,
            )
        )

    if not args.quiet and not args.json and not args.files_with_matches and not args.count:
        s = result.stats
        print(
            f"\n{s.matches} eşleşme, {s.files_matched} dosya, "
            f"{s.files_scanned} taranan, {s.elapsed_ms:.1f} ms",
            file=sys.stderr,
        )

    return 0 if result.matches else 1


def _run_benchmark(args: argparse.Namespace) -> int:
    import shutil
    import subprocess
    import time

    paths = [Path(p) for p in args.paths]
    pattern = args.pattern

    print("=== TurkGrep Benchmark ===\n")

    searcher = Searcher(pattern, ignore_case=args.ignore_case, fixed_strings=args.fixed_strings)
    t0 = time.perf_counter()
    tg_result = searcher.search(paths, respect_gitignore=not args.no_ignore)
    tg_ms = (time.perf_counter() - t0) * 1000

    print(f"TurkGrep : {tg_ms:8.1f} ms | {tg_result.stats.matches} eşleşme | {tg_result.stats.files_scanned} dosya")

    rg = shutil.which("rg")
    if rg:
        cmd = [rg, "--no-heading", "--stats", pattern] + [str(p) for p in paths]
        if args.ignore_case:
            cmd.insert(1, "-i")
        t0 = time.perf_counter()
        proc = subprocess.run(cmd, capture_output=True, text=True)
        rg_ms = (time.perf_counter() - t0) * 1000
        match_count = len([l for l in proc.stdout.splitlines() if l.strip()])
        print(f"Ripgrep  : {rg_ms:8.1f} ms | ~{match_count} satır")

        if tg_ms < rg_ms:
            diff = ((rg_ms - tg_ms) / rg_ms) * 100
            print(f"\nTurkGrep yaklasik %{diff:.0f} daha hizli cikti")
        else:
            print("\nBu testte ripgrep daha hizli (replace/json gibi ekstra ozellikler tg'de var)")
    else:
        print("Ripgrep bulunamadı - karşılaştırma atlandı")

    grep = shutil.which("grep")
    if grep and len(paths) == 1 and paths[0].is_dir():
        cmd = ["grep", "-r", pattern, str(paths[0])]
        if args.ignore_case:
            cmd.insert(1, "-i")
        t0 = time.perf_counter()
        proc = subprocess.run(cmd, capture_output=True, text=True)
        g_ms = (time.perf_counter() - t0) * 1000
        match_count = len(proc.stdout.splitlines())
        print(f"Grep     : {g_ms:8.1f} ms | {match_count} satır")

    return 0
