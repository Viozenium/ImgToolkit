import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox

from theme import (
    BG,
    CARD,
    CARD_HOV,
    ACCENT,
    HIGHLIGHT,
    HIGHLIGHT_ACT,
    BUSY,
    FG,
    MUTED,
    FONT,
    FONT_MONO,
    FONT_CARD,
    FONT_TITLE,
)

HERE = os.path.dirname(os.path.abspath(__file__))

try:
    from info import VERSION
except Exception:
    VERSION = "?"

TOOLS = [
    {
        "key": "finder",
        "title": "Finder",
        "desc": "Analizza una cartella, calcola gli embedding CLIP\ne trova le immagini simili tramite FAISS.",
        "icon": "◈",
        "file": "finder.py",
    },
    {
        "key": "reviewer",
        "title": "Reviewer",
        "desc": "Esamina le coppie simili trovate e decidi\ncosa spostare coppia per coppia.",
        "icon": "◉",
        "file": "reviewer.py",
    },
    {
        "key": "converter",
        "title": "JPG Converter",
        "desc": "Converti immagini PNG · BMP · TIFF · WEBP\nin formato JPG.",
        "icon": "◐",
        "file": "converter.py",
    },
    {
        "key": "manual",
        "title": "Manuale",
        "desc": "Guida d'uso di ImgToolkit, ogni strumento,\nle opzioni e le scorciatoie da tastiera.",
        "icon": "◑",
        "file": "manual.py",
    },
]

class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ImgToolkit - Launcher")
        self.configure(bg=BG)
        self.resizable(False, False)
        self._proc = None
        self._locked_key = None
        self._cards = {}
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build()
        self.update_idletasks()
        self.geometry(f"600x{self.winfo_reqheight()}")

    def _build(self):
        hdr = tk.Frame(self, bg=BG, padx=32, pady=18)
        hdr.pack(fill="x")
        tk.Label(
            hdr,
            text="IMGTOOLKIT",
            font=FONT_TITLE,
            bg=BG,
            fg=HIGHLIGHT,
        ).pack(anchor="w")
        tk.Label(
            hdr,
            text=f"Seleziona uno strumento da avviare  ·  v{VERSION}",
            font=FONT,
            bg=BG,
            fg=MUTED,
        ).pack(anchor="w")
        tk.Frame(self, bg=HIGHLIGHT, height=1).pack(fill="x", padx=32)
        cards_frame = tk.Frame(self, bg=BG, padx=32, pady=16)
        cards_frame.pack(fill="both", expand=True)
        for tool in TOOLS:
            self._make_card(cards_frame, tool)
        tk.Frame(self, bg=ACCENT, height=1).pack(fill="x")
        footer = tk.Frame(self, bg=BG, padx=32, pady=10)
        footer.pack(fill="x")

        self._status = tk.StringVar(value="Nessuno strumento in esecuzione.")
        tk.Label(
            footer, textvariable=self._status, font=FONT_MONO, bg=BG, fg=MUTED
        ).pack(side="left")

        tk.Button(
            footer,
            text="✕ Esci",
            font=FONT_MONO,
            bg=BG,
            fg=MUTED,
            relief="flat",
            bd=0,
            activebackground=HIGHLIGHT,
            activeforeground=FG,
            command=self._on_close,
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            footer,
            text="ℹ Info",
            font=FONT_MONO,
            bg=BG,
            fg=MUTED,
            relief="flat",
            bd=0,
            activebackground=ACCENT,
            activeforeground=FG,
            command=self._open_info,
        ).pack(side="right")

    def _make_card(self, parent, tool):
        card = tk.Frame(parent, bg=CARD, pady=12, padx=20, cursor="hand2")
        card.pack(fill="x", pady=5)

        left = tk.Frame(card, bg=CARD)
        left.pack(side="left", fill="both", expand=True)

        tk.Label(
            left,
            text=f"{tool['icon']}  {tool['title']}",
            font=FONT_CARD,
            bg=CARD,
            fg=FG,
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            left,
            text=tool["desc"],
            font=FONT_MONO,
            bg=CARD,
            fg=MUTED,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(3, 0))

        btn = tk.Button(
            card,
            text="▶ Avvia",
            font=FONT_CARD,
            bg=HIGHLIGHT,
            fg=FG,
            activebackground=HIGHLIGHT_ACT,
            activeforeground=FG,
            relief="flat",
            bd=0,
            padx=14,
            pady=7,
            command=lambda t=tool: self._launch(t),
        )
        btn.pack(side="right", padx=(12, 0))

        self._cards[tool["key"]] = {"card": card, "btn": btn, "tool": tool}
        self._bind_hover(card, card)

    # --------------------------------------------------------------------
    # HOVER

    def _bind_hover(self, widget, card):
        widget.bind("<Enter>", lambda e, c=card: self._on_enter(c))
        widget.bind("<Leave>", lambda e, c=card: self._on_leave(e, c))
        for child in widget.winfo_children():
            self._bind_hover(child, card)

    def _on_enter(self, card):
        if self._locked_key:
            return
        self._set_card_bg(card, CARD_HOV)

    def _on_leave(self, event, card):
        if self._locked_key:
            return
        cx, cy = card.winfo_rootx(), card.winfo_rooty()
        cw, ch = card.winfo_width(), card.winfo_height()
        if cx <= event.x_root < cx + cw and cy <= event.y_root < cy + ch:
            return
        self._set_card_bg(card, CARD)

    def _set_card_bg(self, widget, bg):
        try:
            if not isinstance(widget, tk.Button):
                widget.configure(bg=bg)
        except Exception:
            pass
        for child in widget.winfo_children():
            self._set_card_bg(child, bg)

    # --------------------------------------------------------------------
    # AVVIO

    def _launch(self, tool):
        if getattr(sys, "frozen", False):
            messagebox.showerror(
                "Non supportato",
                "Il launcher in versione exe non può avviare gli script "
                "con sys.executable.",
            )
            return

        script = os.path.join(HERE, tool["file"])
        if not os.path.exists(script):
            messagebox.showerror("Errore", f"File non trovato:\n{script}")
            return

        try:
            self._proc = subprocess.Popen([sys.executable, script], cwd=HERE)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile avviare {tool['title']}:\n{e}")
            return

        self._locked_key = tool["key"]
        self._lock_ui()
        self._status.set(f"▶ {tool['title']} in esecuzione…")
        self._poll()

    def _poll(self):
        if self._proc and self._proc.poll() is None:
            self.after(300, self._poll)
        else:
            exit_code = self._proc.returncode if self._proc else 0
            tool_title = ""
            if self._locked_key and self._locked_key in self._cards:
                tool_title = self._cards[self._locked_key]["tool"]["title"]
            self._proc = None
            self._locked_key = None
            self._unlock_ui()
            if exit_code:
                self._status.set(
                    f"⚠ {tool_title} terminato con errore (codice {exit_code})"
                )
            else:
                self._status.set("Nessuno strumento in esecuzione.")

    def _lock_ui(self):
        for key, data in self._cards.items():
            if key != self._locked_key:
                data["btn"].configure(state="disabled", bg=ACCENT)
            else:
                data["btn"].configure(
                    text="⏳ In esecuzione", state="disabled", bg=BUSY
                )

    def _unlock_ui(self):
        for key, data in self._cards.items():
            data["btn"].configure(state="normal", bg=HIGHLIGHT, text="▶ Avvia")
            self._set_card_bg(data["card"], CARD)

    # --------------------------------------------------------------------
    # CHIUSURA

    def _on_close(self):
        if self._proc and self._proc.poll() is None:
            tool_title = ""
            if self._locked_key and self._locked_key in self._cards:
                tool_title = self._cards[self._locked_key]["tool"]["title"]
            if not messagebox.askyesno(
                "Strumento in esecuzione",
                f"{tool_title} è ancora aperto e continuerà a funzionare "
                "da solo.\nChiudere comunque il launcher?",
            ):
                return
        self.destroy()

    # --------------------------------------------------------------------
    # INFO

    def _open_info(self):
        try:
            import info

            info.main(self)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire info.py:\n{e}")


if __name__ == "__main__":
    Launcher().mainloop()
