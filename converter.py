import datetime
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from converter_core import FORMATS, _convert_to_jpg
from theme import (
    ACCENT,
    BG,
    CARD,
    ENTRY_BG,
    FG,
    FONT,
    FONT_BOLD,
    FONT_HEADER,
    FONT_MONO,
    HIGHLIGHT,
    HIGHLIGHT_ACT,
    MUTED,
)

# --------------------------------------------------------------------
# GUI


def converter_main(parent, standalone=False):
    root = tk.Toplevel(parent)
    root.title("JPG Converter")
    root.geometry("700x620")
    root.resizable(False, False)
    root.configure(bg=BG)

    selected_paths = []

    # --------------------------------------------------------------------
    # Stato della conversione
    # serve sia per chiedere conferma alla chiusura sia per non far parlare il thread con una finestra ormai distrutta.

    stato = {"in_corso": False, "chiusa": False}

    def safe_after(fn, *args):
        """after() dal worker: no-op se la finestra è già stata chiusa."""
        if stato["chiusa"]:
            return
        try:
            root.after(0, fn, *args)
        except (tk.TclError, RuntimeError):
            pass

    def safe_exit():
        if stato["in_corso"] and not messagebox.askyesno(
            "Conversione in corso",
            "La conversione non è ancora finita: chiudendo si interrompe.\n"
            "I file già convertiti restano al loro posto.\n\nChiudere comunque?",
            parent=root,
        ):
            return
        stato["chiusa"] = True
        try:
            root.destroy()
        except Exception:
            pass
        if standalone:
            try:
                parent.destroy()
            except Exception:
                pass

    root.protocol("WM_DELETE_WINDOW", safe_exit)

    # --------------------------------------------------------------------
    # Barra del titolo

    tk.Frame(root, bg=HIGHLIGHT, height=3).pack(fill="x")
    hdr = tk.Frame(root, bg=BG, padx=28, pady=16)
    hdr.pack(fill="x")
    tk.Label(
        hdr,
        text="◈  JPG CONVERTER",
        font=FONT_HEADER,
        bg=BG,
        fg=HIGHLIGHT,
    ).pack(anchor="w")
    tk.Label(
        hdr, text="Converti immagini selezionate in JPG", font=FONT, bg=BG, fg=MUTED
    ).pack(anchor="w")
    tk.Frame(root, bg=HIGHLIGHT, height=1).pack(fill="x")

    # --------------------------------------------------------------------
    # Scheda configurazione

    card = tk.Frame(root, bg=CARD, padx=24, pady=18)
    card.pack(fill="x", padx=24, pady=16)

    def entry_row(
        parent_w, label_text, var, browse_cmd, browse_label="Sfoglia…", readonly=False
    ):
        f = tk.Frame(parent_w, bg=CARD)
        f.pack(fill="x", pady=5)
        tk.Label(
            f, text=label_text, font=FONT, bg=CARD, fg=MUTED, width=22, anchor="w"
        ).pack(side="left")
        e = tk.Entry(
            f,
            textvariable=var,
            font=FONT_MONO,
            bg=ENTRY_BG,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            bd=4,
        )
        if readonly:
            e.config(state="readonly", readonlybackground=ENTRY_BG)
        e.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Button(
            f,
            text=browse_label,
            font=FONT,
            bg=ACCENT,
            fg=FG,
            activebackground=HIGHLIGHT,
            activeforeground=FG,
            relief="flat",
            bd=0,
            padx=10,
            command=browse_cmd,
        ).pack(side="left")

    # --------------------------------------------------------------------
    # File da convertire

    files_var = tk.StringVar(value="Nessun file selezionato")
    format_vars = {ext: tk.BooleanVar(value=True) for _, ext in FORMATS}

    def browse_files():
        active_exts = [ext for ext, var in format_vars.items() if var.get()]
        if not active_exts:
            log_message("⚠️  Seleziona almeno un formato da convertire.")
            return
        pattern = " ".join(f"*{e}" for e in active_exts)
        paths = filedialog.askopenfilenames(
            parent=root,
            title="Seleziona immagini da convertire",
            filetypes=[("Immagini selezionate", pattern), ("Tutti i file", "*.*")],
        )
        if paths:
            selected_paths.clear()
            selected_paths.extend(paths)
            files_var.set(
                paths[0] if len(paths) == 1 else f"{len(paths)} file selezionati"
            )
            if not dest_var.get():
                dest_var.set(os.path.dirname(paths[0]))

    entry_row(card, "File da convertire:", files_var, browse_files, readonly=True)
    dest_var = tk.StringVar()

    def browse_dest():
        path = filedialog.askdirectory(
            parent=root, title="Seleziona cartella di destinazione"
        )
        if path:
            dest_var.set(path)

    entry_row(card, "Cartella destinazione:", dest_var, browse_dest)

    # --------------------------------------------------------------------
    # Selezione formati

    fmt_outer = tk.Frame(card, bg=CARD)
    fmt_outer.pack(fill="x", pady=(10, 0))
    tk.Label(
        fmt_outer,
        text="Formati da convertire:",
        font=FONT,
        bg=CARD,
        fg=MUTED,
        width=22,
        anchor="w",
    ).pack(side="left")

    fmt_box = tk.Frame(fmt_outer, bg=CARD)
    fmt_box.pack(side="left", fill="x")

    for label, ext in FORMATS:
        var = format_vars[ext]
        cb = tk.Checkbutton(
            fmt_box,
            text=label,
            variable=var,
            font=FONT,
            bg=CARD,
            fg=FG,
            activebackground=CARD,
            activeforeground=FG,
            selectcolor=ACCENT,
            relief="flat",
            bd=0,
        )
        cb.pack(side="left", padx=(0, 12))

    # --------------------------------------------------------------------
    # Qualità JPEG

    q_outer = tk.Frame(card, bg=CARD)
    q_outer.pack(fill="x", pady=(10, 0))
    tk.Label(
        q_outer,
        text="Qualità JPEG:",
        font=FONT,
        bg=CARD,
        fg=MUTED,
        width=22,
        anchor="w",
    ).pack(side="left")
    quality_var = tk.IntVar(value=100)
    tk.Spinbox(
        q_outer,
        from_=50,
        to=100,
        textvariable=quality_var,
        font=FONT_MONO,
        bg=ENTRY_BG,
        fg=FG,
        buttonbackground=ACCENT,
        relief="flat",
        bd=4,
        width=6,
    ).pack(side="left")
    tk.Label(
        q_outer,
        text="(95 = visivamente identico, file ~metà)",
        font=FONT_MONO,
        bg=CARD,
        fg=MUTED,
    ).pack(side="left", padx=(10, 0))

    # --------------------------------------------------------------------
    # Barra azioni (ancorata prima del log per garantirne la visibilità)

    tk.Frame(root, bg=ACCENT, height=1).pack(fill="x", side="bottom")
    bar = tk.Frame(root, bg=BG, height=64)
    bar.pack(fill="x", side="bottom")
    bar.pack_propagate(False)

    status_var = tk.StringVar(value="Pronto.")
    tk.Label(bar, textvariable=status_var, font=FONT, bg=BG, fg=MUTED).pack(
        side="left", padx=28
    )

    tk.Button(
        bar,
        text="Chiudi",
        font=FONT_BOLD,
        bg=ACCENT,
        fg=FG,
        activebackground=HIGHLIGHT,
        activeforeground=FG,
        relief="flat",
        bd=0,
        padx=16,
        pady=8,
        command=safe_exit,
    ).pack(side="right", padx=(8, 28), pady=12)

    convert_btn = tk.Button(
        bar,
        text="▶  Converti",
        font=FONT_BOLD,
        bg=HIGHLIGHT,
        fg=FG,
        activebackground=HIGHLIGHT_ACT,
        activeforeground=FG,
        relief="flat",
        bd=0,
        padx=16,
        pady=8,
    )
    convert_btn.pack(side="right", pady=12)

    # --------------------------------------------------------------------
    # Riquadro log

    log_frame = tk.Frame(root, bg=BG, padx=24)
    log_frame.pack(fill="both", expand=True)
    log_box = tk.Text(
        log_frame,
        font=FONT_MONO,
        bg=CARD,
        fg=FG,
        insertbackground=FG,
        relief="flat",
        bd=0,
        state="disabled",
        wrap="none",
    )
    sb = tk.Scrollbar(log_frame, command=log_box.yview, bg=CARD)
    log_box.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    log_box.pack(fill="both", expand=True)

    # --------------------------------------------------------------------
    # Funzioni interne

    def log_message(msg):
        ts = datetime.datetime.now().strftime("[%H:%M:%S] ")
        log_box.config(state="normal")
        log_box.insert("end", ts + msg + "\n")
        log_box.see("end")
        log_box.config(state="disabled")

    def on_progress(done, total):
        status_var.set(f"Conversione… {done}/{total}")

    def on_done():
        stato["in_corso"] = False
        convert_btn.config(state="normal", bg=HIGHLIGHT, text="▶  Converti")
        status_var.set("Pronto.")

    def start_convert():
        active_exts = {ext for ext, var in format_vars.items() if var.get()}
        to_convert = [
            p for p in selected_paths if os.path.splitext(p)[1].lower() in active_exts
        ]

        if not selected_paths:
            log_message("⚠️  Seleziona prima i file da convertire.")
            return
        if not to_convert:
            log_message("⚠️  Nessun file corrisponde ai formati selezionati.")
            return
        dest = dest_var.get().strip()
        if not dest or not os.path.isdir(dest):
            log_message("⚠️  Seleziona una cartella di destinazione valida.")
            return

        try:
            quality = max(50, min(100, int(quality_var.get())))
        except (tk.TclError, ValueError):
            quality = 100

        skipped = len(selected_paths) - len(to_convert)
        if skipped:
            log_message(f"ℹ️  {skipped} file ignorati (formato non selezionato)")

        stato["in_corso"] = True
        convert_btn.config(state="disabled", bg=ACCENT, text="⏳ In corso…")
        status_var.set(f"Conversione di {len(to_convert)} file…")
        log_message(
            f"Inizio conversione di {len(to_convert)} file → {dest}  (qualità {quality})"
        )
        threading.Thread(
            target=_convert_to_jpg,
            args=(
                dest,
                to_convert,
                quality,
                lambda m: safe_after(log_message, m),
                lambda d, t: safe_after(on_progress, d, t),
                lambda: safe_after(on_done),
            ),
            daemon=True,
        ).start()

    convert_btn.config(command=start_convert)
    return root


# --------------------------------------------------------------------
# AVVIO AUTONOMO


def _standalone():
    if sys.platform.startswith("win"):
        import multiprocessing

        multiprocessing.freeze_support()
    root = tk.Tk()
    root.withdraw()
    converter_main(root, standalone=True)
    root.mainloop()


if __name__ == "__main__" and not getattr(sys, "frozen", False):
    _standalone()
