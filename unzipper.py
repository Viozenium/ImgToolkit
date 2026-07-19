import zipfile
import tkinter as tk
from tkinter import filedialog
import threading
import os
import datetime

BG = "#1a1a2e"
CARD = "#16213e"
ACCENT = "#0f3460"
HIGHLIGHT = "#e94560"
ENTRY_BG = "#0d1b2a"
FG = "#eaeaea"
MUTED = "#7a7f9a"
FONT = ("Courier New", 10)
FONT_BOLD = ("Courier New", 10, "bold")
FONT_MONO = ("Courier New", 9)

# --------------------------------------------------------------------
# LOGICA


def _is_encrypted(zip_ref):
    """True se almeno un file nello zip è protetto da password."""
    return any(info.flag_bits & 0x1 for info in zip_ref.infolist())


def _unzip(cartella, zips, delete_after=False, log=None, progress=None, fine=None):
    ok, failed, locked, deleted = 0, 0, 0, 0
    total = len(zips)
    for i, filename in enumerate(zips, start=1):
        zip_path = os.path.join(cartella, filename)
        extract_dir = os.path.join(cartella, os.path.splitext(filename)[0])
        extracted = False
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                if _is_encrypted(zip_ref):
                    locked += 1
                    if log:
                        log(f"🔒 ZIP protetto da password: {filename}")
                    continue
                if os.path.isdir(extract_dir) and os.listdir(extract_dir):
                    if log:
                        log(
                            f"ℹ️  '{os.path.basename(extract_dir)}' già esistente, sovrascrivo"
                        )
                os.makedirs(extract_dir, exist_ok=True)
                zip_ref.extractall(extract_dir)
            ok += 1
            extracted = True
            if log:
                log(f"✅ {filename}")
        except zipfile.BadZipFile:
            failed += 1
            if log:
                log(f"❎ {filename}: file zip corrotto o non valido")
        except Exception as e:
            failed += 1
            if log:
                log(f"❎ {filename}: {e}")
        finally:
            if extracted and delete_after:
                try:
                    os.remove(zip_path)
                    deleted += 1
                    if log:
                        log(f"🗑️  Eliminato: {filename}")
                except Exception as e:
                    if log:
                        log(f"⚠️  Impossibile eliminare {filename}: {e}")
            if progress:
                progress(i, total)
    if log:
        parts = [f"{ok} estratti"]
        if deleted:
            parts.append(f"{deleted} zip eliminati")
        if failed:
            parts.append(f"{failed} falliti")
        if locked:
            parts.append(f"{locked} protetti da password")
        log(f"── {', '.join(parts)} ──")
    if fine:
        fine()


# --------------------------------------------------------------------
# GUI


def unzip_main(parent, standalone=False):
    root = tk.Toplevel(parent)
    root.title("Unzipper")
    root.geometry("700x520")
    root.resizable(False, False)
    root.configure(bg=BG)

    def safe_exit():
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
        hdr, text="◈  UNZIPPER", font=("Courier New", 16, "bold"), bg=BG, fg=HIGHLIGHT
    ).pack(anchor="w")
    tk.Label(
        hdr,
        text="Decomprimi tutti i file .zip presenti in una cartella",
        font=FONT,
        bg=BG,
        fg=MUTED,
    ).pack(anchor="w")
    tk.Frame(root, bg=HIGHLIGHT, height=1).pack(fill="x")

    # --------------------------------------------------------------------
    # Scheda configurazione
    card = tk.Frame(root, bg=CARD, padx=24, pady=18)
    card.pack(fill="x", padx=24, pady=16)

    folder_var = tk.StringVar()

    def browse_folder():
        path = filedialog.askdirectory(
            parent=root, title="Seleziona la cartella con i file .zip"
        )
        if path:
            folder_var.set(path)

    f = tk.Frame(card, bg=CARD)
    f.pack(fill="x", pady=5)
    tk.Label(
        f,
        text="Cartella con i .zip:",
        font=FONT,
        bg=CARD,
        fg=MUTED,
        width=22,
        anchor="w",
    ).pack(side="left")
    tk.Entry(
        f,
        textvariable=folder_var,
        font=FONT_MONO,
        bg=ENTRY_BG,
        fg=FG,
        insertbackground=FG,
        relief="flat",
        bd=4,
    ).pack(side="left", fill="x", expand=True, padx=(0, 8))
    tk.Button(
        f,
        text="Sfoglia…",
        font=FONT,
        bg=ACCENT,
        fg=FG,
        activebackground=HIGHLIGHT,
        activeforeground=FG,
        relief="flat",
        bd=0,
        padx=10,
        command=browse_folder,
    ).pack(side="left")

    # --------------------------------------------------------------------
    # Opzioni

    delete_var = tk.BooleanVar(value=False)
    opt = tk.Frame(card, bg=CARD)
    opt.pack(fill="x", pady=(8, 0))
    tk.Label(opt, text="", font=FONT, bg=CARD, fg=MUTED, width=22, anchor="w").pack(
        side="left"
    )
    tk.Checkbutton(
        opt,
        text="Elimina .zip dopo estrazione riuscita",
        variable=delete_var,
        font=FONT,
        bg=CARD,
        fg=FG,
        activebackground=CARD,
        activeforeground=FG,
        selectcolor=ACCENT,
        relief="flat",
        bd=0,
        highlightthickness=0,
    ).pack(side="left")

    # --------------------------------------------------------------------
    # Barra azioni (prima del log)

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

    unz_btn = tk.Button(
        bar,
        text="▶  Decomprimi",
        font=FONT_BOLD,
        bg=HIGHLIGHT,
        fg=FG,
        activebackground="#c73652",
        activeforeground=FG,
        relief="flat",
        bd=0,
        padx=16,
        pady=8,
    )
    unz_btn.pack(side="right", pady=12)

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
        status_var.set(f"Decompressione… {done}/{total}")

    def on_done():
        unz_btn.config(state="normal", bg=HIGHLIGHT, text="▶  Decomprimi")
        status_var.set("Pronto.")

    def start_unzip():
        cartella = folder_var.get().strip()
        if not cartella or not os.path.isdir(cartella):
            log_message("⚠️  Seleziona una cartella valida.")
            return
        zips = sorted(f for f in os.listdir(cartella) if f.lower().endswith(".zip"))
        if not zips:
            log_message("⚠️  Nessun file .zip trovato nella cartella.")
            return
        delete_after = delete_var.get()
        unz_btn.config(state="disabled", bg=ACCENT, text="⏳ In corso…")
        status_var.set(f"Decompressione di {len(zips)} file .zip…")
        log_message(
            f"Trovati {len(zips)} file .zip in: {cartella}"
            + ("  (eliminazione zip attiva)" if delete_after else "")
        )
        threading.Thread(
            target=_unzip,
            args=(
                cartella,
                zips,
                delete_after,
                lambda m: root.after(0, log_message, m),
                lambda d, t: root.after(0, on_progress, d, t),
                lambda: root.after(0, on_done),
            ),
            daemon=True,
        ).start()

    unz_btn.config(command=start_unzip)
    return root


# --------------------------------------------------------------------
# AVVIO AUTONOMO

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    unzip_main(root, standalone=True)
    root.mainloop()
