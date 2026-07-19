import os
import sys
import shutil
import threading
import subprocess
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

INPUT_FILE = "Risultati_somiglianza.txt"
CHECK_FOLDER = os.path.join(os.path.expanduser("~"), "Desktop", "Immagini Duplicate")

os.makedirs(CHECK_FOLDER, exist_ok=True)

# --------------------------------------------------------------------
# PALETTE COLORI

BG = "#1a1a2e"
TABBAR = "#12122a"
TAB_ACT = "#1a1a2e"
TAB_IDLE = "#0d0d1f"
TAB_HOVER = "#14142a"
CARD = "#16213e"
ACCENT = "#0f3460"
HIGHLIGHT = "#e94560"
FG = "#eaeaea"
MUTED = "#7a7f9a"
DONE_CLR = "#2a4a2a"
SKIP_CLR = "#2a2a1a"
FONT = ("Courier New", 10)
FONT_SM = ("Courier New", 9)
FONT_LG = ("Courier New", 13, "bold")

# --------------------------------------------------------------------
# CARICAMENTO


def load_results():
    results = []
    if not os.path.exists(INPUT_FILE):
        return results
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(" | ")
            if len(parts) != 3:
                continue
            a, b, score = parts
            results.append({"a": a, "b": b, "score": float(score), "state": "pending"})
    return results


# --------------------------------------------------------------------
# REVIEWER


class Reviewer:
    def __init__(self, root, pairs):
        self.root = root
        self.pairs = pairs
        self.current = 0
        self._tab_buttons = []
        self._pil_cache = {}
        self._count_done = 0
        self._count_skipped = 0
        self._load_token = 0

        self.root.title("Duplicate Image Manager")
        self.root.configure(bg=BG)
        self.root.geometry("1280x780")
        self.root.minsize(900, 600)
        self._resize_job = None
        self._last_target = None

        self._build_ui()
        self._render_tabs()
        self._show(0)

        # --------------------------------------------------------------------
        # Scorciatoie da tastiera

        self.root.bind("a", lambda e: self._move_a())
        self.root.bind("b", lambda e: self._move_b())
        self.root.bind("s", lambda e: self._move_both())
        self.root.bind("n", lambda e: self._skip())
        self.root.bind("<Left>", lambda e: self._go(self.current - 1))
        self.root.bind("<Right>", lambda e: self._go(self.current + 1))
        self.root.bind("q", lambda e: self.root.destroy())
        self.root.bind("<Configure>", self._on_resize)

    # --------------------------------------------------------------------
    # COSTRUZIONE UI

    def _build_ui(self):

        # --------------------------------------------------------------------
        # Barra schede

        self.tabbar_outer = tk.Frame(self.root, bg=TABBAR, height=38)
        self.tabbar_outer.pack(fill="x", side="top")
        self.tabbar_outer.pack_propagate(False)
        self.tabbar = tk.Frame(self.tabbar_outer, bg=TABBAR)
        self.tabbar.pack(side="left", fill="both", expand=True)
        self.counter_lbl = tk.Label(
            self.tabbar_outer,
            text="",
            font=FONT_SM,
            bg=TABBAR,
            fg=MUTED,
            padx=12,
        )
        self.counter_lbl.pack(side="right", fill="y")
        tk.Frame(self.root, bg=HIGHLIGHT, height=2).pack(fill="x")
        tk.Frame(self.root, bg=ACCENT, height=1).pack(fill="x", side="bottom")
        action_bar = tk.Frame(self.root, bg=BG, height=72)
        action_bar.pack(fill="x", side="bottom")
        action_bar.pack_propagate(False)

        def btn(parent, text, color, cmd, key_hint=""):
            f = tk.Frame(parent, bg=BG)
            f.pack(side="left", padx=8)
            b = tk.Button(
                f,
                text=text,
                font=("Courier New", 10, "bold"),
                bg=color,
                fg=FG,
                activebackground=HIGHLIGHT,
                activeforeground=FG,
                relief="flat",
                bd=0,
                padx=18,
                pady=10,
                command=cmd,
            )
            b.pack(pady=(8, 2))
            if key_hint:
                tk.Label(
                    f, text=key_hint, font=("Courier New", 8), bg=BG, fg=MUTED
                ).pack()
            return b

        lgroup = tk.Frame(action_bar, bg=BG)
        lgroup.pack(side="left", padx=(24, 0))
        btn(lgroup, "↑ MOVE A", "#7b2d42", self._move_a, "tasto A")
        btn(lgroup, "↑ MOVE B", "#7b2d42", self._move_b, "tasto B")
        btn(lgroup, "↑ MOVE BOTH", HIGHLIGHT, self._move_both, "tasto S")

        rgroup = tk.Frame(action_bar, bg=BG)
        rgroup.pack(side="right", padx=(0, 24))
        btn(rgroup, "✕ CHIUDI", "#333355", self.root.destroy, "tasto Q")
        btn(rgroup, "◀ PREV", ACCENT, lambda: self._go(self.current - 1), "← freccia")
        btn(rgroup, "SKIP ▶", ACCENT, self._skip, "tasto N")
        btn(rgroup, "NEXT ▶", ACCENT, lambda: self._go(self.current + 1), "→ freccia")
        content = tk.Frame(self.root, bg=BG)
        content.pack(fill="both", expand=True)

        # --------------------------------------------------------------------
        # Intestazione: punteggio e nomi file

        header = tk.Frame(content, bg=CARD, pady=10)
        header.pack(fill="x", padx=16, pady=(14, 0))

        self.score_lbl = tk.Label(header, text="", font=FONT_LG, bg=CARD, fg=HIGHLIGHT)
        self.score_lbl.pack(side="left", padx=16)

        self.names_lbl = tk.Label(header, text="", font=FONT_SM, bg=CARD, fg=MUTED)
        self.names_lbl.pack(side="left", padx=8)

        self.state_lbl = tk.Label(header, text="", font=FONT, bg=CARD, fg=MUTED)
        self.state_lbl.pack(side="right", padx=16)

        # --------------------------------------------------------------------
        # Pannelli immagini

        img_area = tk.Frame(content, bg=BG)
        img_area.pack(fill="both", expand=True, padx=16, pady=12)

        # --------------------------------------------------------------------
        # Pannello sinistro

        left_wrap = tk.Frame(img_area, bg=CARD)
        left_wrap.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.lbl_a_title = tk.Label(
            left_wrap,
            text="A",
            font=FONT,
            bg=CARD,
            fg=MUTED,
            anchor="w",
            padx=10,
            pady=4,
        )
        self.lbl_a_title.pack(fill="x")
        tk.Frame(left_wrap, bg=ACCENT, height=1).pack(fill="x")

        self.img_lbl_a = tk.Label(
            left_wrap, bg=CARD, cursor="hand2", fg=MUTED, font=FONT
        )
        self.img_lbl_a.pack(fill="both", expand=True, padx=8, pady=8)
        self.img_lbl_a.bind(
            "<Button-1>", lambda e: self._open_file(self.pairs[self.current]["a"])
        )

        # --------------------------------------------------------------------
        # Pannello destro

        right_wrap = tk.Frame(img_area, bg=CARD)
        right_wrap.pack(side="right", fill="both", expand=True, padx=(6, 0))

        self.lbl_b_title = tk.Label(
            right_wrap,
            text="B",
            font=FONT,
            bg=CARD,
            fg=MUTED,
            anchor="w",
            padx=10,
            pady=4,
        )
        self.lbl_b_title.pack(fill="x")
        tk.Frame(right_wrap, bg=ACCENT, height=1).pack(fill="x")

        self.img_lbl_b = tk.Label(
            right_wrap, bg=CARD, cursor="hand2", fg=MUTED, font=FONT
        )
        self.img_lbl_b.pack(fill="both", expand=True, padx=8, pady=8)
        self.img_lbl_b.bind(
            "<Button-1>", lambda e: self._open_file(self.pairs[self.current]["b"])
        )

    # --------------------------------------------------------------------
    # SCHEDE

    def _render_tabs(self):
        MAX_VISIBLE = 30
        start = max(0, self.current - MAX_VISIBLE // 2)
        visible = self.pairs[start : start + MAX_VISIBLE]
        existing = self.tabbar.winfo_children()
        need_rebuild = len(existing) != len(visible)

        if need_rebuild:
            for w in existing:
                w.destroy()
            self._tab_buttons = []

        color_map_state = {"done": "#3a5a3a", "skipped": "#3a3a1a"}

        for rel_i, pair in enumerate(visible):
            abs_i = start + rel_i
            state = pair["state"]
            is_active = abs_i == self.current
            tab_bg = TAB_ACT if is_active else TAB_IDLE
            bg = color_map_state.get(state, tab_bg)
            fg = FG if is_active else MUTED
            label = f" {abs_i + 1}  {pair['score']:.2f} "

            if need_rebuild:
                tab = tk.Frame(self.tabbar, bg=bg, padx=0, pady=0)
                tab.pack(side="left", fill="y", padx=(0, 1))
                accent = tk.Frame(tab, bg=HIGHLIGHT if is_active else bg, height=2)
                accent.pack(fill="x")
                inner = tk.Button(
                    tab,
                    text=label,
                    font=FONT_SM,
                    bg=bg,
                    fg=fg,
                    activebackground=TAB_HOVER,
                    activeforeground=FG,
                    relief="flat",
                    bd=0,
                    padx=6,
                    pady=6,
                    command=lambda i=abs_i: self._go(i),
                )
                inner.pack(fill="both", expand=True)
                inner._accent = accent
                self._tab_buttons.append(inner)
            else:
                inner = self._tab_buttons[rel_i]
                tab = inner.master
                inner.configure(
                    text=label, bg=bg, fg=fg, command=lambda i=abs_i: self._go(i)
                )
                tab.configure(bg=bg)
                accent_color = HIGHLIGHT if is_active else bg
                inner._accent.configure(bg=accent_color)

        self.counter_lbl.config(
            text=f"{self.current + 1}/{len(self.pairs)}  ✓{self._count_done}  ↷{self._count_skipped}"
        )

    # --------------------------------------------------------------------
    # VISUALIZZAZIONE

    def _show(self, index):
        if not self.pairs:
            messagebox.showinfo("Vuoto", "Nessuna coppia trovata.")
            self.root.destroy()
            return

        index = max(0, min(index, len(self.pairs) - 1))
        self.current = index
        pair = self.pairs[index]
        self._load_pair_async(pair["a"], pair["b"])
        self.score_lbl.config(text=f"sim = {pair['score']:.4f}")
        self.names_lbl.config(
            text=f"{os.path.basename(pair['a'])}  ↔  {os.path.basename(pair['b'])}"
        )
        state_map = {
            "pending": "- in attesa",
            "done": "✓ spostata",
            "skipped": "↷ saltata",
        }
        self.state_lbl.config(text=state_map.get(pair["state"], ""))
        self.lbl_a_title.config(text=f"  A  ·  {os.path.basename(pair['a'])}")
        self.lbl_b_title.config(text=f"  B  ·  {os.path.basename(pair['b'])}")

        self._render_tabs()

    # --------------------------------------------------------------------
    # RIDIMENSIONAMENTO

    def _on_resize(self, event):
        if event.widget is not self.root:
            return
        if self._resize_job is not None:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(300, self._resize_done)

    def _resize_done(self):
        self._resize_job = None
        w = max(self.img_lbl_a.winfo_width(), 500)
        h = max(self.img_lbl_a.winfo_height(), 440)
        target = (w, h)
        if target == self._last_target:
            return
        self._last_target = target
        self._pil_cache.clear()
        if self.pairs:
            pair = self.pairs[self.current]
            self._load_pair_async(pair["a"], pair["b"])

    # --------------------------------------------------------------------
    # CARICAMENTO IMMAGINI ASINCRONO

    def _load_pair_async(self, path_a, path_b):
        self.root.update_idletasks()
        w = max(self.img_lbl_a.winfo_width(), 500)
        h = max(self.img_lbl_a.winfo_height(), 440)
        target = (w, h)
        self._last_target = target
        self._load_token += 1
        token = self._load_token

        threading.Thread(
            target=self._load_pair_worker,
            args=(path_a, path_b, target, token),
            daemon=True,
        ).start()

    def _load_pair_worker(self, path_a, path_b, target, token):
        """Solo lavoro PIL qui: niente oggetti Tk fuori dal main thread."""
        results = {}
        for path, key in [(path_a, "a"), (path_b, "b")]:
            if path in self._pil_cache:
                self._pil_cache[path] = self._pil_cache.pop(path)
                results[key] = self._pil_cache[path]
            else:
                img = self._load_image_fast(path, target)
                results[key] = img
                if img is not None:
                    self._pil_cache[path] = img
                    if len(self._pil_cache) > 20:
                        self._pil_cache.pop(next(iter(self._pil_cache)))
        if token == self._load_token:
            self.root.after(0, self._apply_images, results["a"], results["b"], token)

    def _apply_images(self, pil_a, pil_b, token):
        """Gira nel main thread: qui è sicuro creare i PhotoImage."""
        if token != self._load_token:
            return
        for pil_img, lbl in [(pil_a, self.img_lbl_a), (pil_b, self.img_lbl_b)]:
            if pil_img is not None:
                ph = ImageTk.PhotoImage(pil_img)
                lbl.config(image=ph, text="")
                lbl.image = ph
            else:
                lbl.config(
                    image="", text="⚠ immagine non caricabile\n(spostata o corrotta?)"
                )
                lbl.image = None

    def _load_image_fast(self, path, target):
        """Ritorna un'immagine PIL ridimensionata (NON un PhotoImage)."""
        try:
            tw, th = target
            with Image.open(path) as src:
                ow, oh = src.size
                scale = max(ow / tw, oh / th)
                if scale >= 8:
                    src.draft("RGB", (ow // 8, oh // 8))
                elif scale >= 4:
                    src.draft("RGB", (ow // 4, oh // 4))
                elif scale >= 2:
                    src.draft("RGB", (ow // 2, oh // 2))
                img = src.convert("RGB")
            img.thumbnail(target, Image.BILINEAR)
            return img
        except Exception:
            return None

    # --------------------------------------------------------------------
    # AZIONI

    def _move(self, path):
        """Sposta in CHECK_FOLDER evitando di sovrascrivere file omonimi."""
        if not os.path.exists(path):
            return
        base = os.path.basename(path)
        dest = os.path.join(CHECK_FOLDER, base)
        if os.path.exists(dest):
            name, ext = os.path.splitext(base)
            n = 1
            while os.path.exists(os.path.join(CHECK_FOLDER, f"{name}_{n}{ext}")):
                n += 1
            dest = os.path.join(CHECK_FOLDER, f"{name}_{n}{ext}")
        shutil.move(path, dest)
        self._pil_cache.pop(path, None)

    def _move_a(self):
        self._move(self.pairs[self.current]["a"])
        self._set_state(self.current, "done")
        self._advance()

    def _move_b(self):
        self._move(self.pairs[self.current]["b"])
        self._set_state(self.current, "done")
        self._advance()

    def _move_both(self):
        self._move(self.pairs[self.current]["a"])
        self._move(self.pairs[self.current]["b"])
        self._set_state(self.current, "done")
        self._advance()

    def _skip(self):
        self._set_state(self.current, "skipped")
        self._advance()

    def _set_state(self, index, new_state):
        old_state = self.pairs[index]["state"]
        if old_state == new_state:
            return
        self.pairs[index]["state"] = new_state
        if old_state == "done":
            self._count_done -= 1
        elif old_state == "skipped":
            self._count_skipped -= 1
        if new_state == "done":
            self._count_done += 1
        elif new_state == "skipped":
            self._count_skipped += 1

    def _advance(self):
        pending = [i for i, p in enumerate(self.pairs) if p["state"] == "pending"]
        if pending:
            next_i = next((i for i in pending if i > self.current), pending[0])
            self._show(next_i)
        else:
            self._render_tabs()
            messagebox.showinfo("Completato", "Tutte le coppie sono state processate!")

    def _go(self, index):
        if 0 <= index < len(self.pairs):
            self._show(index)

    def _open_file(self, path):
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.call(["open", path])
            else:
                subprocess.call(["xdg-open", path])
        except Exception:
            pass


# --------------------------------------------------------------------
# ESECUZIONE


def run():
    if not os.path.exists(INPUT_FILE):
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Errore", f"File non trovato: {INPUT_FILE}")
        return

    pairs = load_results()
    if not pairs:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Vuoto", "Nessun risultato nel file.")
        return

    root = tk.Tk()
    Reviewer(root, pairs)
    root.mainloop()


if __name__ == "__main__":
    run()
