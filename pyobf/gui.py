#!/usr/bin/env python3
# language: Python 3.9+, file: pyobf/gui.py
# GUI front-end for the pyobf toolkit: pick a .py file, choose layers, obfuscate.
# Design: black background, mint lines.
#
# The heavy work lives in run_job() (no Tk) so it can be tested headlessly and
# runs in a background thread so the window never freezes during Cython builds.

import os
import platform
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import obfuscator          # noqa: E402
import build_native        # noqa: E402

# --------------------------------------------------------------------------- #
# Palette: black + mint. Single source of truth.
# --------------------------------------------------------------------------- #
C = {
    "bg":        "#000000",
    "surface":   "#070a09",
    "mint":      "#3fe0b0",
    "mint_dim":  "#1d4f44",
    "mint_hot":  "#5bffcc",
    "text":      "#d8f5ec",
    "muted":     "#6b8a80",
    "danger":    "#ff5c5c",
}


# --------------------------------------------------------------------------- #
# Worker (no Tk) — this is what the button runs. Testable in isolation.
# --------------------------------------------------------------------------- #
def run_job(input_path, out_dir, *, strings, rename, layers, native, log):
    """Obfuscate input_path into out_dir. log(msg) receives progress lines.
    Returns (ok: bool, out_path: str | None)."""
    if not input_path or not input_path.lower().endswith(".py"):
        log("ERROR: input must be a .py file")
        return False, None
    if not os.path.isfile(input_path):
        log(f"ERROR: file not found: {input_path}")
        return False, None

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            source = f.read()
    except OSError as e:
        log(f"ERROR: cannot read file: {e}")
        return False, None

    import ast
    try:
        ast.parse(source)
    except SyntaxError as e:
        log(f"ERROR: source has a syntax error: {e}")
        return False, None

    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(input_path))[0]

    if native:
        if not stem.isidentifier():
            log(f"ERROR: '{stem}' is not a valid module name for native build")
            return False, None
        log("compiling to native extension (Cython)...")
        if strings:
            log("  - encrypting string/bytes literals first")
        try:
            dst = build_native.build(input_path, stem, strings, out_dir)
        except Exception as e:  # compiler/toolchain failures surface here
            log(f"ERROR: native build failed:\n{e}")
            return False, None
        log(f"done -> {dst}")
        log(f"NOTE: bound to {sys.platform} / CPython "
            f"{sys.version_info.major}.{sys.version_info.minor}")
        return True, dst

    # Pure-Python path
    applied = [n for n, on in (("strings", strings), ("rename", rename),
                               (f"{layers}x pack", layers > 0)) if on]
    log("obfuscating: " + (", ".join(applied) if applied else "no layers"))
    result = obfuscator.obfuscate(source, strings=strings, rename=rename,
                                  layers=layers)
    out_path = os.path.join(out_dir, stem + ".obf.py")
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(result)
    except OSError as e:
        log(f"ERROR: cannot write output: {e}")
        return False, None
    log(f"done -> {out_path} ({len(result)} bytes)")
    return True, out_path


# --------------------------------------------------------------------------- #
# GUI
# --------------------------------------------------------------------------- #
class ObfGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("pyobf")
        root.configure(bg=C["bg"])
        root.geometry("640x560")
        root.minsize(600, 520)

        self.in_var = tk.StringVar()
        self.out_var = tk.StringVar()
        self.v_strings = tk.BooleanVar(value=True)
        self.v_rename = tk.BooleanVar(value=True)
        self.v_pack = tk.BooleanVar(value=True)
        self.v_layers = tk.IntVar(value=2)
        self.v_native = tk.BooleanVar(value=False)
        self._last_out = None

        pad = {"padx": 20}
        tk.Label(root, text="pyobf", bg=C["bg"], fg=C["mint"],
                 font=("Consolas", 22, "bold")).pack(anchor="w", pady=(18, 0),
                                                     **pad)
        tk.Label(root, text="drop in a .py file — get it obfuscated",
                 bg=C["bg"], fg=C["muted"], font=("Segoe UI", 10)).pack(
                 anchor="w", pady=(0, 14), **pad)

        self._file_row(root, "INPUT  .py", self.in_var, self._pick_in, pad)
        self._file_row(root, "OUTPUT dir", self.out_var, self._pick_out, pad)

        # Options box (mint outline)
        box = self._mint_box(root)
        box.pack(fill="x", pady=12, **pad)
        inner = tk.Frame(box, bg=C["bg"])
        inner.pack(fill="x", padx=14, pady=12)
        tk.Label(inner, text="LAYERS", bg=C["bg"], fg=C["mint"],
                 font=("Consolas", 10, "bold")).grid(row=0, column=0,
                 columnspan=3, sticky="w", pady=(0, 8))
        self._check(inner, "string / bytes encryption", self.v_strings, 1, 0)
        self._check(inner, "rename locals", self.v_rename, 1, 1)
        self._check(inner, "bytecode packing", self.v_pack, 2, 0,
                    cmd=self._sync)
        lay = tk.Frame(inner, bg=C["bg"])
        lay.grid(row=2, column=1, sticky="w", pady=4)
        tk.Label(lay, text="x", bg=C["bg"], fg=C["muted"]).pack(side="left")
        self.sp = tk.Spinbox(lay, from_=1, to=5, width=3, textvariable=self.v_layers,
                             bg=C["surface"], fg=C["text"], buttonbackground=C["surface"],
                             relief="flat", highlightthickness=1,
                             highlightbackground=C["mint_dim"], justify="center")
        self.sp.pack(side="left", padx=(4, 0))
        self._check(inner, "native compile (Cython .so/.pyd)  — strongest",
                    self.v_native, 3, 0, span=2, cmd=self._sync)

        # Run button
        self.run_btn = self._ghost(root, "OBFUSCATE", self._run, big=True)
        self.run_btn.pack(fill="x", pady=(4, 10), **pad)

        # Log
        logbox = self._mint_box(root)
        logbox.pack(fill="both", expand=True, pady=(0, 16), **pad)
        self.log = tk.Text(logbox, bg=C["surface"], fg=C["mint"],
                           insertbackground=C["mint"], relief="flat",
                           font=("Consolas", 10), height=8, wrap="word",
                           state="disabled")
        self.log.pack(fill="both", expand=True, padx=2, pady=2)

        self.open_btn = self._ghost(root, "open output folder", self._open_folder)
        # shown after a successful run

        self._sync()

    # ---- small widget builders ----
    def _mint_box(self, parent):
        return tk.Frame(parent, bg=C["mint_dim"], bd=0,
                        highlightbackground=C["mint_dim"], highlightthickness=1)

    def _file_row(self, parent, label, var, cmd, pad):
        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x", pady=4, **pad)
        tk.Label(row, text=label, bg=C["bg"], fg=C["mint"], width=11,
                 anchor="w", font=("Consolas", 10)).pack(side="left")
        e = tk.Entry(row, textvariable=var, bg=C["surface"], fg=C["text"],
                     insertbackground=C["text"], relief="flat",
                     highlightthickness=1, highlightbackground=C["mint_dim"],
                     highlightcolor=C["mint"], font=("Consolas", 10))
        e.pack(side="left", fill="x", expand=True, ipady=5, padx=(8, 8))
        self._ghost(row, "browse", cmd).pack(side="left")

    def _check(self, parent, text, var, r, col, span=1, cmd=None):
        cb = tk.Checkbutton(parent, text=text, variable=var, command=cmd,
                            bg=C["bg"], fg=C["text"], selectcolor=C["surface"],
                            activebackground=C["bg"], activeforeground=C["mint"],
                            font=("Segoe UI", 10), anchor="w",
                            highlightthickness=0, bd=0)
        cb.grid(row=r, column=col, columnspan=span, sticky="w", pady=4, padx=(0, 16))

    def _ghost(self, parent, text, cmd, big=False):
        b = tk.Button(parent, text=text, command=cmd, bg=C["bg"], fg=C["mint"],
                      activebackground=C["mint"], activeforeground=C["bg"],
                      relief="solid", bd=1, cursor="hand2",
                      highlightbackground=C["mint"],
                      font=("Consolas", 12 if big else 9, "bold" if big else "normal"),
                      pady=10 if big else 3, padx=12)
        b.bind("<Enter>", lambda e: b.configure(bg=C["mint"], fg=C["bg"]))
        b.bind("<Leave>", lambda e: b.configure(bg=C["bg"], fg=C["mint"]))
        return b

    # ---- behavior ----
    def _sync(self):
        # native overrides pure-python-only layers
        native = self.v_native.get()
        state = "disabled" if native else "normal"
        self.sp.configure(state=state)
        if native:
            self.v_rename.set(False)
            self.v_pack.set(False)

    def _pick_in(self):
        p = filedialog.askopenfilename(filetypes=[("Python", "*.py")])
        if p:
            self.in_var.set(p)
            if not self.out_var.get():
                self.out_var.set(os.path.join(os.path.dirname(p), "obf_out"))

    def _pick_out(self):
        p = filedialog.askdirectory()
        if p:
            self.out_var.set(p)

    def _logline(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _run(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.open_btn.pack_forget()
        self.run_btn.configure(state="disabled", text="working...")

        args = dict(
            input_path=self.in_var.get().strip(),
            out_dir=self.out_var.get().strip() or ".",
            strings=self.v_strings.get(),
            rename=self.v_rename.get(),
            layers=self.v_layers.get() if self.v_pack.get() else 0,
            native=self.v_native.get(),
        )

        def worker():
            ok, out = run_job(**args, log=lambda m: self.root.after(0, self._logline, m))
            self.root.after(0, self._done, ok, out)

        threading.Thread(target=worker, daemon=True).start()

    def _done(self, ok, out):
        self.run_btn.configure(state="normal", text="OBFUSCATE")
        self._last_out = out
        if ok and out:
            self.open_btn.pack(pady=(0, 16), padx=20, anchor="e")

    def _open_folder(self):
        if not self._last_out:
            return
        folder = os.path.dirname(os.path.abspath(self._last_out))
        try:
            if platform.system() == "Windows":
                os.startfile(folder)  # noqa: no-member (Windows only)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            self._logline(f"could not open folder: {e}")


def main():
    root = tk.Tk()
    ObfGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
