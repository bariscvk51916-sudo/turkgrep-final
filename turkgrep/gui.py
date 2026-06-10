# basit tkinter arayuzu
from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from . import __version__
from .output import format_replace_text, format_search_text
from .replacer import Replacer
from .searcher import Searcher


class TurkGrepApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"TurkGrep v{__version__}")
        self.root.minsize(720, 520)
        self.root.geometry("900x640")

        self.path_var = tk.StringVar(value=str(Path.cwd() / "test_samples"))
        self.pattern_var = tk.StringVar()
        self.replace_var = tk.StringVar()
        self.ignore_case_var = tk.BooleanVar(value=False)
        self.line_numbers_var = tk.BooleanVar(value=True)
        self.dry_run_var = tk.BooleanVar(value=True)
        self.file_type_var = tk.StringVar()

        self._build_ui()

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(
            main,
            text="TurkGrep",
            font=("Segoe UI", 14, "bold"),
        )
        title.pack(anchor=tk.W, pady=(0, 10))

        form = ttk.LabelFrame(main, text="Ayarlar", padding=10)
        form.pack(fill=tk.X)

        ttk.Label(form, text="Klasör / Dosya:").grid(row=0, column=0, sticky=tk.W, pady=4)
        path_row = ttk.Frame(form)
        path_row.grid(row=0, column=1, sticky=tk.EW, pady=4)
        ttk.Entry(path_row, textvariable=self.path_var, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_row, text="Seç...", command=self._pick_path).pack(side=tk.LEFT, padx=(6, 0))

        ttk.Label(form, text="Aranacak desen:").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Entry(form, textvariable=self.pattern_var, width=50).grid(row=1, column=1, sticky=tk.EW, pady=4)

        ttk.Label(form, text="Yeni değer (opsiyonel):").grid(row=2, column=0, sticky=tk.W, pady=4)
        ttk.Entry(form, textvariable=self.replace_var, width=50).grid(row=2, column=1, sticky=tk.EW, pady=4)

        ttk.Label(form, text="Dosya türü:").grid(row=3, column=0, sticky=tk.W, pady=4)
        ttk.Entry(form, textvariable=self.file_type_var, width=10).grid(row=3, column=1, sticky=tk.W, pady=4)
        ttk.Label(form, text="ör: py, js, java").grid(row=3, column=1, sticky=tk.W, padx=(80, 0))

        opts = ttk.Frame(form)
        opts.grid(row=4, column=1, sticky=tk.W, pady=6)
        ttk.Checkbutton(opts, text="Büyük/küçük harf duyarsız", variable=self.ignore_case_var).pack(side=tk.LEFT)
        ttk.Checkbutton(opts, text="Satır numarası", variable=self.line_numbers_var).pack(side=tk.LEFT, padx=12)
        ttk.Checkbutton(opts, text="Değiştirmede önizleme", variable=self.dry_run_var).pack(side=tk.LEFT, padx=12)

        form.columnconfigure(1, weight=1)

        btns = ttk.Frame(main)
        btns.pack(fill=tk.X, pady=10)
        ttk.Button(btns, text="Ara", command=self._run_search).pack(side=tk.LEFT)
        ttk.Button(btns, text="Değiştir", command=self._run_replace).pack(side=tk.LEFT, padx=8)
        ttk.Button(btns, text="Benchmark", command=self._run_benchmark).pack(side=tk.LEFT, padx=8)
        ttk.Button(btns, text="Temizle", command=self._clear_output).pack(side=tk.LEFT, padx=8)

        self.status_var = tk.StringVar(value="Hazır")
        ttk.Label(main, textvariable=self.status_var).pack(anchor=tk.W)

        out_frame = ttk.LabelFrame(main, text="Sonuc", padding=6)
        out_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        self.output = scrolledtext.ScrolledText(out_frame, wrap=tk.NONE, font=("Consolas", 10))
        self.output.pack(fill=tk.BOTH, expand=True)

    def _pick_path(self) -> None:
        selected = filedialog.askdirectory(title="Aranacak klasörü seç")
        if selected:
            self.path_var.set(selected)

    def _clear_output(self) -> None:
        self.output.delete("1.0", tk.END)
        self.status_var.set("Hazır")

    def _append_output(self, text: str) -> None:
        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)

    def _validate(self) -> Path | None:
        pattern = self.pattern_var.get().strip()
        if not pattern:
            messagebox.showwarning("Uyarı", "Aranacak desen boş olamaz.")
            return None

        path = Path(self.path_var.get().strip())
        if not path.exists():
            messagebox.showerror("Hata", f"Yol bulunamadı:\n{path}")
            return None
        return path

    def _extensions(self) -> set[str] | None:
        ext = self.file_type_var.get().strip().lstrip(".")
        return {ext} if ext else None

    def _run_async(self, worker) -> None:
        self.status_var.set("Çalışıyor...")
        threading.Thread(target=worker, daemon=True).start()

    def _run_search(self) -> None:
        path = self._validate()
        if not path:
            return

        pattern = self.pattern_var.get().strip()

        def worker():
            try:
                searcher = Searcher(pattern, ignore_case=self.ignore_case_var.get())
                result = searcher.search([path], extensions=self._extensions())
                text = format_search_text(
                    result,
                    pattern=pattern,
                    line_numbers=self.line_numbers_var.get(),
                    color=False,
                )
                s = result.stats
                footer = (
                    f"\n--- {s.matches} eşleşme | {s.files_matched} dosya | "
                    f"{s.elapsed_ms:.1f} ms ---"
                )
                self.root.after(0, lambda: self._append_output(text + footer))
                self.root.after(0, lambda: self.status_var.set("Arama tamamlandı"))
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror("Hata", str(exc)))
                self.root.after(0, lambda: self.status_var.set("Hata oluştu"))

        self._run_async(worker)

    def _run_replace(self) -> None:
        path = self._validate()
        if not path:
            return

        pattern = self.pattern_var.get().strip()
        replacement = self.replace_var.get()
        if not replacement and not self.dry_run_var.get():
            if not messagebox.askyesno("Onay", "Yeni değer boş. Eşleşmeler silinecek. Devam?"):
                return

        dry_run = self.dry_run_var.get()

        def worker():
            try:
                replacer = Replacer(
                    pattern,
                    replacement,
                    ignore_case=self.ignore_case_var.get(),
                )
                result = replacer.replace(
                    [path],
                    dry_run=dry_run,
                    extensions=self._extensions(),
                    backup=not dry_run,
                )
                text = format_replace_text(result, dry_run=dry_run, color=False)
                self.root.after(0, lambda: self._append_output(text))
                self.root.after(0, lambda: self.status_var.set("Değiştirme tamamlandı"))
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror("Hata", str(exc)))
                self.root.after(0, lambda: self.status_var.set("Hata oluştu"))

        self._run_async(worker)

    def _run_benchmark(self) -> None:
        path = self._validate()
        if not path:
            return

        pattern = self.pattern_var.get().strip()

        def worker():
            import shutil
            import subprocess
            import time

            lines = ["=== Benchmark ===", ""]
            try:
                searcher = Searcher(pattern, ignore_case=self.ignore_case_var.get())
                t0 = time.perf_counter()
                tg_result = searcher.search([path], extensions=self._extensions())
                tg_ms = (time.perf_counter() - t0) * 1000
                lines.append(
                    f"TurkGrep : {tg_ms:8.1f} ms | {tg_result.stats.matches} eşleşme"
                )

                rg = shutil.which("rg")
                if rg:
                    cmd = [rg, "--no-heading", pattern, str(path)]
                    if self.ignore_case_var.get():
                        cmd.insert(1, "-i")
                    t0 = time.perf_counter()
                    proc = subprocess.run(cmd, capture_output=True, text=True)
                    rg_ms = (time.perf_counter() - t0) * 1000
                    cnt = len([l for l in proc.stdout.splitlines() if l.strip()])
                    lines.append(f"Ripgrep  : {rg_ms:8.1f} ms | ~{cnt} satır")
                    if tg_ms < rg_ms:
                        diff = ((rg_ms - tg_ms) / rg_ms) * 100
                        lines.append(f"\nTurkGrep %{diff:.0f} daha hizli")
                    else:
                        lines.append("\nBu sefer ripgrep daha hizli cikti")
                else:
                    lines.append("Ripgrep bulunamadı")

                self.root.after(0, lambda: self._append_output("\n".join(lines)))
                self.root.after(0, lambda: self.status_var.set("Benchmark tamamlandı"))
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror("Hata", str(exc)))
                self.root.after(0, lambda: self.status_var.set("Hata oluştu"))

        self._run_async(worker)


def main() -> None:
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except tk.TclError:
        pass
    TurkGrepApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
