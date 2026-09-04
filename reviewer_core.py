"""Lettura dei risultati, spostamento dei doppioni e caricamento immagini.

Tutto quello che il Reviewer fa su file e immagini, senza tkinter di mezzo:
si può usare (e provare) senza aprire una finestra.
"""

import os
import shutil
import subprocess
import sys

from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

INPUT_FILE = "Risultati_somiglianza.txt"
CHECK_FOLDER = os.path.join(os.path.expanduser("~"), "Desktop", "Immagini Duplicate")


# --------------------------------------------------------------------
# RISULTATI


def load_results(input_file=INPUT_FILE):
    """Legge le coppie prodotte da Finder: 'percorso a | percorso b | score'."""
    results = []
    if not os.path.exists(input_file):
        return results
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(" | ")
            if len(parts) != 3:
                continue
            a, b, score = parts
            results.append({"a": a, "b": b, "score": float(score), "state": "pending"})
    return results


# --------------------------------------------------------------------
# SPOSTAMENTO


def move_to_check_folder(path, folder=CHECK_FOLDER):
    """Sposta il file evitando di sovrascrivere omonimi. Ritorna la destinazione.

    Ritorna None se il file non c'è più, capita quando la stessa immagine compare in più coppie ed è già stata spostata.

    La cartella viene creata qui e non all'import, aprire il modulo senza spostare nulla non deve lasciare cartelle sul Desktop.
    """
    if not os.path.exists(path):
        return None
    os.makedirs(folder, exist_ok=True)
    base = os.path.basename(path)
    dest = os.path.join(folder, base)
    if os.path.exists(dest):
        name, ext = os.path.splitext(base)
        n = 1
        while os.path.exists(os.path.join(folder, f"{name}_{n}{ext}")):
            n += 1
        dest = os.path.join(folder, f"{name}_{n}{ext}")
    shutil.move(path, dest)
    return dest


# --------------------------------------------------------------------
# IMMAGINI


def load_image_fast(path, target):
    """Ritorna un'immagine PIL ridimensionata (NON un PhotoImage).

    Il draft di JPEG evita di decodificare a piena risoluzione quello che poi verrebbe comunque rimpicciolito.
    """
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


def open_in_system_viewer(path):
    """Apre il file con il visualizzatore predefinito del sistema."""
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.call(["open", path])
        else:
            subprocess.call(["xdg-open", path])
    except Exception:
        pass
