import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from finder_core import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_OUTPUT_FILE,
    DEFAULT_SIM_THRESHOLD,
    MAX_CPU_THREADS,
    build_index,
    compute_embeddings,
    default_cpu_threads,
    device,
    find_and_save,
    load_images,
    load_model,
    set_cpu_threads,
)
from theme import (
    BG,
    CARD,
    ACCENT,
    HIGHLIGHT,
    HIGHLIGHT_ACT,
    DANGER,
    WHITE,
    ENTRY_BG,
    FG,
    MUTED_SOFT as MUTED,
    FONT_LABEL,
    FONT_MONO,
    FONT_CARD,
    FONT_TITLE,
)

# --------------------------------------------------------------------
# GUI


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Duplicate Finder")
        self.resizable(False, False)
        self.configure(bg=BG)

        self._running = False
        self._closing = False
        self._stop_event = threading.Event()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()

    # --------------------------------------------------------------------
    # COSTRUZIONE UI

    def _build_ui(self):
        # --------------------------------------------------------------------
        # Titolo
        title_frame = tk.Frame(self, bg=BG, padx=24, pady=16)
        title_frame.pack(fill="x")
        tk.Label(
            title_frame,
            text="◈  DUPLICATE FINDER",
            font=FONT_TITLE,
            bg=BG,
            fg=HIGHLIGHT,
        ).pack(anchor="w")
        tk.Label(
            title_frame,
            text=f"CLIP · ViT-B-32 · FAISS · device: {device.upper()}",
            font=FONT_LABEL,
            bg=BG,
            fg=MUTED,
        ).pack(anchor="w")

        tk.Frame(self, bg=HIGHLIGHT, height=1).pack(fill="x", padx=24)

        # --------------------------------------------------------------------
        # Scheda principale
        card = tk.Frame(self, bg=CARD, padx=24, pady=20)
        card.pack(fill="x", padx=24, pady=16)

        def row(parent, label, widget_factory, **kw):
            f = tk.Frame(parent, bg=CARD)
            f.pack(fill="x", pady=5)
            tk.Label(
                f, text=label, font=FONT_LABEL, bg=CARD, fg=MUTED, width=22, anchor="w"
            ).pack(side="left")
            w = widget_factory(f, **kw)
            w.pack(side="left", fill="x", expand=True)
            return w

        folder_frame = tk.Frame(card, bg=CARD)
        folder_frame.pack(fill="x", pady=5)
        tk.Label(
            folder_frame,
            text="Cartella immagini:",
            font=FONT_LABEL,
            bg=CARD,
            fg=MUTED,
            width=22,
            anchor="w",
        ).pack(side="left")
        self.folder_var = tk.StringVar()
        tk.Entry(
            folder_frame,
            textvariable=self.folder_var,
            font=FONT_MONO,
            bg=ENTRY_BG,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            bd=4,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Button(
            folder_frame,
            text="Sfoglia…",
            font=FONT_LABEL,
            bg=ACCENT,
            fg=FG,
            activebackground=HIGHLIGHT,
            activeforeground=FG,
            relief="flat",
            bd=0,
            padx=10,
            command=self._browse_folder,
        ).pack(side="left")

        out_frame = tk.Frame(card, bg=CARD)
        out_frame.pack(fill="x", pady=5)
        tk.Label(
            out_frame,
            text="File output:",
            font=FONT_LABEL,
            bg=CARD,
            fg=MUTED,
            width=22,
            anchor="w",
        ).pack(side="left")
        self.output_var = tk.StringVar(value=DEFAULT_OUTPUT_FILE)
        tk.Entry(
            out_frame,
            textvariable=self.output_var,
            font=FONT_MONO,
            bg=ENTRY_BG,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            bd=4,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Button(
            out_frame,
            text="Salva come…",
            font=FONT_LABEL,
            bg=ACCENT,
            fg=FG,
            activebackground=HIGHLIGHT,
            activeforeground=FG,
            relief="flat",
            bd=0,
            padx=10,
            command=self._browse_output,
        ).pack(side="left")

        params_frame = tk.Frame(card, bg=CARD)
        params_frame.pack(fill="x", pady=(12, 0))

        def spin(parent, default, from_, to_, width=7):
            v = tk.IntVar(value=default)
            s = tk.Spinbox(
                parent,
                from_=from_,
                to=to_,
                textvariable=v,
                font=FONT_MONO,
                bg=ENTRY_BG,
                fg=FG,
                buttonbackground=ACCENT,
                relief="flat",
                bd=4,
                width=width,
            )
            return s, v

        for col_label, col_key, col_default, col_from, col_to in [
            ("Batch size", "batch", DEFAULT_BATCH_SIZE, 1, 512),
            ("Limite thread CPU", "threads", default_cpu_threads(), 1, MAX_CPU_THREADS),
        ]:
            cf = tk.Frame(params_frame, bg=CARD)
            cf.pack(side="left", padx=(0, 20))
            tk.Label(cf, text=col_label, font=FONT_LABEL, bg=CARD, fg=MUTED).pack(
                anchor="w"
            )
            s, v = spin(cf, col_default, col_from, col_to)
            s.pack()
            setattr(self, f"_{col_key}_var", v)

        checks = tk.Frame(params_frame, bg=CARD)
        checks.pack(side="left", padx=(0, 0))
        self._cache_var = tk.BooleanVar(value=True)
        self._recursive_var = tk.BooleanVar(value=False)
        for text, var in [
            ("Usa cache embeddings", self._cache_var),
            ("Includi sottocartelle", self._recursive_var),
        ]:
            tk.Checkbutton(
                checks,
                text=text,
                variable=var,
                font=FONT_LABEL,
                bg=CARD,
                fg=FG,
                activebackground=CARD,
                activeforeground=FG,
                selectcolor=ENTRY_BG,
                relief="flat",
                bd=0,
                highlightthickness=0,
                anchor="w",
            ).pack(anchor="w")

        thresh_frame = tk.Frame(card, bg=CARD)
        thresh_frame.pack(fill="x", pady=(14, 0))
        tk.Label(
            thresh_frame, text="Soglia similarità:", font=FONT_LABEL, bg=CARD, fg=MUTED
        ).pack(anchor="w")
        slider_row = tk.Frame(thresh_frame, bg=CARD)
        slider_row.pack(fill="x")
        self._thresh_var = tk.DoubleVar(value=DEFAULT_SIM_THRESHOLD)
        self._thresh_label = tk.Label(
            slider_row,
            text=f"{DEFAULT_SIM_THRESHOLD:.2f}",
            font=FONT_LABEL,
            bg=CARD,
            fg=HIGHLIGHT,
            width=5,
        )
        self._thresh_label.pack(side="right")
        tk.Scale(
            slider_row,
            from_=0.5,
            to=1.0,
            resolution=0.01,
            orient="horizontal",
            variable=self._thresh_var,
            bg=CARD,
            fg=FG,
            troughcolor=ACCENT,
            highlightthickness=0,
            bd=0,
            showvalue=False,
            command=self._on_thresh,
        ).pack(side="left", fill="x", expand=True)

        # --------------------------------------------------------------------
        # Barra di avanzamento
        prog_frame = tk.Frame(self, bg=BG, padx=24)
        prog_frame.pack(fill="x")
        self._progress = ttk.Progressbar(prog_frame, length=600, mode="determinate")
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "TProgressbar", troughcolor=CARD, background=HIGHLIGHT, thickness=6
        )
        self._progress.pack(fill="x", pady=(0, 6))

        # --------------------------------------------------------------------
        # Riquadro log
        log_frame = tk.Frame(self, bg=BG, padx=24)
        log_frame.pack(fill="x")
        self._log_box = tk.Text(
            log_frame,
            height=10,
            font=FONT_MONO,
            bg=CARD,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            bd=0,
            state="disabled",
            wrap="none",
        )
        scrollbar = tk.Scrollbar(log_frame, command=self._log_box.yview, bg=CARD)
        self._log_box.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._log_box.pack(fill="x")

        # --------------------------------------------------------------------
        # Tabella risultati
        results_frame = tk.Frame(self, bg=BG, padx=24, pady=8)
        results_frame.pack(fill="both", expand=True)

        res_header = tk.Frame(results_frame, bg=BG)
        res_header.pack(fill="x")
        self._res_label = tk.Label(
            res_header, text="Risultati trovati", font=FONT_LABEL, bg=BG, fg=MUTED
        )
        self._res_label.pack(side="left", anchor="w")
        self._page_lbl = tk.Label(res_header, text="", font=FONT_LABEL, bg=BG, fg=MUTED)
        self._page_lbl.pack(side="right")
        tk.Button(
            res_header,
            text="▶",
            font=FONT_LABEL,
            bg=ACCENT,
            fg=FG,
            relief="flat",
            bd=0,
            padx=8,
            command=self._next_page,
        ).pack(side="right", padx=2)
        tk.Button(
            res_header,
            text="◀",
            font=FONT_LABEL,
            bg=ACCENT,
            fg=FG,
            relief="flat",
            bd=0,
            padx=8,
            command=self._prev_page,
        ).pack(side="right", padx=2)

        cols = ("Immagine A", "Immagine B", "Score")
        self._tree = ttk.Treeview(
            results_frame, columns=cols, show="headings", height=8
        )
        style.configure(
            "Treeview",
            background=CARD,
            foreground=FG,
            fieldbackground=CARD,
            font=FONT_MONO,
            rowheight=22,
        )
        style.configure(
            "Treeview.Heading", background=ACCENT, foreground=FG, font=FONT_LABEL
        )
        style.map("Treeview", background=[("selected", ACCENT)])
        for c, w in zip(cols, [280, 280, 80]):
            self._tree.heading(c, text=c)
            self._tree.column(c, width=w, anchor="w")
        vsb = ttk.Scrollbar(results_frame, orient="vertical", command=self._tree.yview)
        hsb = ttk.Scrollbar(
            results_frame, orient="horizontal", command=self._tree.xview
        )
        self._tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self._tree.pack(fill="both", expand=True)

        self._all_results = []
        self._page = 0
        self._page_size = 200

        # --------------------------------------------------------------------
        # Barra inferiore (sempre visibile)
        tk.Frame(self, bg=HIGHLIGHT, height=1).pack(fill="x", padx=24)
        bottom = tk.Frame(self, bg=BG, padx=24, pady=14)
        bottom.pack(fill="x", side="bottom")

        self._status_var = tk.StringVar(value="Pronto.")
        tk.Label(
            bottom, textvariable=self._status_var, font=FONT_LABEL, bg=BG, fg=MUTED
        ).pack(side="left")

        self._run_btn = tk.Button(
            bottom,
            text="▶  AVVIA ANALISI",
            font=FONT_CARD,
            bg=HIGHLIGHT,
            fg=WHITE,
            activebackground=HIGHLIGHT_ACT,
            activeforeground=WHITE,
            relief="flat",
            bd=0,
            padx=24,
            pady=10,
            command=self._toggle_run,
        )
        self._run_btn.pack(side="right")

        tk.Button(
            bottom,
            text="Chiudi",
            font=FONT_CARD,
            bg=ACCENT,
            fg=WHITE,
            activebackground=HIGHLIGHT,
            activeforeground=WHITE,
            relief="flat",
            bd=0,
            padx=16,
            pady=10,
            command=self._on_close,
        ).pack(side="right", padx=(0, 8))

        # --------------------------------------------------------------------
        # Dimensione finestra: adatta al contenuto, poi blocca la larghezza

        self.update_idletasks()
        w = max(self.winfo_reqwidth(), 760)
        h = max(self.winfo_reqheight(), 780)
        self.geometry(f"{w}x{h}")
        self.minsize(w, 600)

    # --------------------------------------------------------------------
    # HELPER THREAD-SAFE

    def _on_close(self):
        self._closing = True
        self._stop_event.set()
        self.destroy()

    def _safe_after(self, fn, *args):
        """after() dal worker: no-op se la finestra è già stata chiusa."""
        if not self._closing:
            try:
                self.after(0, fn, *args)
            except tk.TclError:
                pass

    # --------------------------------------------------------------------
    # CALLBACK

    def _on_thresh(self, val):
        self._thresh_label.config(text=f"{float(val):.2f}")

    def _browse_folder(self):
        path = filedialog.askdirectory(title="Seleziona cartella immagini")
        if path:
            self.folder_var.set(path)

    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Salva risultati come…",
            defaultextension=".txt",
            filetypes=[("Text file", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self.output_var.set(path)

    def _log(self, msg):
        def _do():
            self._log_box.configure(state="normal")
            self._log_box.insert("end", msg + "\n")
            self._log_box.see("end")
            self._log_box.configure(state="disabled")

        self._safe_after(_do)

    def _set_progress(self, val, eta=""):
        self._progress["value"] = val
        if eta:
            self._status_var.set(f"Embeddings… {val}% — {eta}")
        elif self._running:
            self._status_var.set(f"Embeddings… {val}%")

    def _set_status(self, msg):
        self._status_var.set(msg)

    # --------------------------------------------------------------------
    # AVVIO / ARRESTO

    def _toggle_run(self):
        if self._running:
            self._stop_event.set()
            self._run_btn.configure(state="disabled", text="⏳ ARRESTO…")
            self._set_status("Arresto in corso…")
        else:
            self._start()

    def _start(self):
        folder = self.folder_var.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Errore", "Seleziona una cartella valida.")
            return

        output_file = self.output_var.get().strip() or DEFAULT_OUTPUT_FILE
        batch_size = self._batch_var.get()
        cpu_threads = self._threads_var.get()
        threshold = self._thresh_var.get()
        use_cache = self._cache_var.get()
        recursive = self._recursive_var.get()

        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")
        for row in self._tree.get_children():
            self._tree.delete(row)
        self._progress["value"] = 0
        self._stop_event.clear()
        self._running = True
        self._run_btn.configure(text="■  STOP", bg=DANGER)
        self._set_status("In esecuzione…")

        def finish(status_msg):
            self._running = False
            self._safe_after(
                lambda: self._run_btn.configure(
                    state="normal",
                    text="▶  AVVIA ANALISI",
                    bg=HIGHLIGHT,
                )
            )
            self._safe_after(self._set_status, status_msg)

        def task():
            try:
                set_cpu_threads(cpu_threads, self._log)
                load_model(self._log)
                if self._stop_event.is_set():
                    self._log("⏹️    Interrotto dall'utente.")
                    finish("Interrotto.")
                    return

                self._log("📂    Caricamento immagini…")
                paths = load_images(folder, recursive=recursive)
                if not paths:
                    self._log("⚠️    Nessuna immagine trovata.")
                    finish("Nessuna immagine trovata.")
                    return
                self._log(
                    f"   → {len(paths)} immagini trovate"
                    + (" (incluse sottocartelle)" if recursive else "")
                )

                self._log("Calcolo embeddings…")
                embeddings, paths = compute_embeddings(
                    paths,
                    folder,
                    batch_size,
                    use_cache,
                    self._stop_event,
                    self._log,
                    lambda v, eta="": self._safe_after(self._set_progress, v, eta),
                )
                if self._stop_event.is_set():
                    self._log("⏹️    Interrotto dall'utente.")
                    finish("Interrotto.")
                    return
                if embeddings is None:
                    self._log("⚠️    Nessuna immagine leggibile.")
                    finish("Nessuna immagine leggibile.")
                    return

                self._log("Costruzione indice FAISS…")
                index = build_index(embeddings)

                self._log(f"Ricerca similarità (soglia={threshold:.2f})…")
                results = find_and_save(
                    index,
                    embeddings,
                    paths,
                    threshold,
                    output_file,
                    self._log,
                    stop_event=self._stop_event,
                )
                if self._stop_event.is_set():
                    self._log("⏹️    Interrotto dall'utente.")
                    finish("Interrotto.")
                    return

                self._safe_after(self._populate_results, results)
                finish(f"Completato — {len(results)} coppie trovate")

            except Exception as e:
                self._log(f"❌    Errore: {e}")
                finish("Errore durante l'esecuzione")

        threading.Thread(target=task, daemon=True).start()

    def _populate_results(self, results):
        self._all_results = results
        self._page = 0
        self._render_page()

    def _render_page(self):
        for row in self._tree.get_children():
            self._tree.delete(row)
        total = len(self._all_results)
        page_size = self._page_size
        start = self._page * page_size
        end = min(start + page_size, total)
        for a, b, s in self._all_results[start:end]:
            self._tree.insert(
                "",
                "end",
                values=(
                    os.path.basename(a),
                    os.path.basename(b),
                    f"{s:.4f}",
                ),
            )
        total_pages = max(1, -(-total // page_size))  # ceil div
        self._page_lbl.config(
            text=(
                f"pag. {self._page + 1}/{total_pages}  ({start + 1}–{end} di {total})"
                if total
                else "Nessun risultato"
            )
        )

    def _next_page(self):
        total_pages = max(1, -(-len(self._all_results) // self._page_size))
        if self._page < total_pages - 1:
            self._page += 1
            self._render_page()

    def _prev_page(self):
        if self._page > 0:
            self._page -= 1
            self._render_page()


# --------------------------------------------------------------------
# PUNTO D'INGRESSO

if __name__ == "__main__":
    app = App()
    app.mainloop()
