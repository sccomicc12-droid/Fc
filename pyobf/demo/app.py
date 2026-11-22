# language: Python 3.9+, file: demo/app.py
# Tkinter GUI over the (obfuscated/compiled) license_core module.
#
# license_core is imported normally: drop the compiled
# license_core*.so (Linux) / license_core*.pyd (Windows) from pyobf's
# build_native.py next to this file, and Python loads the native module
# instead of the .py. The GUI never contains the secret logic.

import tkinter as tk
from tkinter import font as tkfont

import license_core

# --------------------------------------------------------------------------- #
# PALETTE — single source of truth for color. PLACEHOLDER VALUES.
# Replace these hex codes with the club web-dev project colors and the whole UI
# re-themes. Nothing else needs to change.
# --------------------------------------------------------------------------- #
PALETTE = {
    "bg":            "#0f1115",   # window background
    "surface":       "#1a1d24",   # card background
    "border":        "#2a2e37",
    "primary":       "#5b8def",   # main action button
    "primary_hover": "#4a7bd8",
    "accent":        "#8b5cf6",   # secondary action
    "accent_hover":  "#7a4de0",
    "text":          "#e6e8ec",
    "text_muted":    "#9aa0a9",
    "success":       "#3fb950",
    "danger":        "#f85149",
}

_PLACEHOLDER = "XXXX-XXXX-XXXX-XXXX"


class KeyGuardApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        p = PALETTE
        root.title("KeyGuard — License Validator")
        root.configure(bg=p["bg"])
        root.geometry("460x360")
        root.minsize(460, 360)

        self.f_title = tkfont.Font(family="Segoe UI", size=18, weight="bold")
        self.f_body = tkfont.Font(family="Segoe UI", size=11)
        self.f_mono = tkfont.Font(family="Consolas", size=13)
        self.f_small = tkfont.Font(family="Segoe UI", size=9)

        wrap = tk.Frame(root, bg=p["bg"])
        wrap.pack(fill="both", expand=True, padx=24, pady=20)

        tk.Label(wrap, text="KeyGuard", font=self.f_title,
                 bg=p["bg"], fg=p["text"]).pack(anchor="w")
        tk.Label(wrap, text="Enter a license key to validate.",
                 font=self.f_body, bg=p["bg"], fg=p["text_muted"]).pack(
                 anchor="w", pady=(2, 16))

        # Key entry
        self.entry = tk.Entry(wrap, font=self.f_mono, justify="center",
                              bg=p["surface"], fg=p["text"],
                              insertbackground=p["text"],
                              relief="flat", highlightthickness=1,
                              highlightbackground=p["border"],
                              highlightcolor=p["primary"])
        self.entry.insert(0, _PLACEHOLDER)
        self.entry.configure(fg=p["text_muted"])
        self.entry.bind("<FocusIn>", self._clear_placeholder)
        self.entry.bind("<Return>", lambda e: self._validate())
        self.entry.pack(fill="x", ipady=8)

        # Buttons
        btns = tk.Frame(wrap, bg=p["bg"])
        btns.pack(fill="x", pady=14)
        self._mk_button(btns, "Validate", p["primary"], p["primary_hover"],
                        self._validate).pack(side="left", expand=True, fill="x",
                                             padx=(0, 6))
        self._mk_button(btns, "Generate", p["accent"], p["accent_hover"],
                        self._generate).pack(side="left", expand=True, fill="x",
                                             padx=(6, 0))

        # Result card
        self.card = tk.Frame(wrap, bg=p["surface"], highlightthickness=1,
                             highlightbackground=p["border"])
        self.card.pack(fill="both", expand=True, pady=(4, 0))
        self.status = tk.Label(self.card, text="—", font=self.f_title,
                               bg=p["surface"], fg=p["text_muted"])
        self.status.pack(pady=(18, 4))
        self.detail = tk.Label(self.card, text="awaiting input",
                               font=self.f_body, bg=p["surface"],
                               fg=p["text_muted"])
        self.detail.pack(pady=(0, 16))

    def _mk_button(self, parent, text, color, hover, cmd):
        b = tk.Button(parent, text=text, command=cmd, font=self.f_body,
                      bg=color, fg="#ffffff", activebackground=hover,
                      activeforeground="#ffffff", relief="flat",
                      bd=0, cursor="hand2", pady=9)
        b.bind("<Enter>", lambda e: b.configure(bg=hover))
        b.bind("<Leave>", lambda e: b.configure(bg=color))
        return b

    def _clear_placeholder(self, _evt):
        if self.entry.get() == _PLACEHOLDER:
            self.entry.delete(0, "end")
            self.entry.configure(fg=PALETTE["text"])

    def _current_key(self) -> str:
        v = self.entry.get().strip()
        return "" if v == _PLACEHOLDER else v

    def _validate(self):
        p = PALETTE
        key = self._current_key()
        if license_core.validate_key(key):
            tier = license_core.key_tier(key)
            self.status.configure(text="VALID", fg=p["success"])
            self.detail.configure(text=f"Tier: {tier}", fg=p["text"])
        else:
            self.status.configure(text="INVALID", fg=p["danger"])
            self.detail.configure(text="key rejected", fg=p["text_muted"])

    def _generate(self):
        key = license_core.generate_key()
        self.entry.delete(0, "end")
        self.entry.configure(fg=PALETTE["text"])
        self.entry.insert(0, key)
        self._validate()


def main():
    root = tk.Tk()
    KeyGuardApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
