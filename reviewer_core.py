"""Lettura dei risultati, spostamento dei doppioni e caricamento immagini.

Tutto quello che il Reviewer fa su file e immagini, senza tkinter di mezzo:
si può usare (e provare) senza aprire una finestra.
"""

import json
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
# STATO DELLA REVISIONE

# Le decisioni prese finiscono in un file affiancato ai risultati, non nei risultati stessi
# quelli restano il dato prodotto dal Finder, e si può sempre ricominciare da capo.
# La chiave è la coppia di percorsi, non la posizione nell'elenco, così rilanciando il Finder con un'altra soglia le coppie che ricompaiono si riprendono la decisione già presa.

STATE_SUFFIX = ".stato.json"


def state_path(input_file=INPUT_FILE):
    return os.path.splitext(input_file)[0] + STATE_SUFFIX


def load_state(input_file=INPUT_FILE):
    """Ritorna {(a, b): stato} di una revisione precedente, {} se non c'è."""
    percorso = state_path(input_file)
    if not os.path.isfile(percorso):
        return {}
    try:
        with open(percorso, encoding="utf-8") as f:
            dati = json.load(f)
    except (OSError, ValueError):
        return {}
    return {
        (voce["a"], voce["b"]): voce["state"]
        for voce in dati.get("pairs", [])
        if voce.get("state") in ("done", "skipped") and voce.get("a") and voce.get("b")
    }


def save_state(pairs, input_file=INPUT_FILE, undo=None):
    """Salva le coppie già decise e la pila degli annullamenti.

    Scrive su file temporaneo e poi rinomina, così un'interruzione non lascia
    uno stato mezzo scritto. Se non resta nulla da decidere il file viene
    rimosso: a revisione finita non ha più motivo di esistere.
    """
    percorso = state_path(input_file)
    decise = [
        {"a": p["a"], "b": p["b"], "state": p["state"]}
        for p in pairs
        if p["state"] != "pending"
    ]
    if not decise or all(p["state"] != "pending" for p in pairs):
        clear_state(input_file)
        return
    tmp = percorso + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                {"version": 2, "pairs": decise, "undo": undo or []},
                f,
                ensure_ascii=False,
            )
        os.replace(tmp, percorso)
    except OSError:
        pass


def load_undo(input_file=INPUT_FILE):
    """Pila degli annullamenti salvata, così Z funziona anche dopo una riapertura."""
    percorso = state_path(input_file)
    if not os.path.isfile(percorso):
        return []
    try:
        with open(percorso, encoding="utf-8") as f:
            dati = json.load(f)
    except (OSError, ValueError):
        return []
    azioni = []
    for voce in dati.get("undo", []):
        try:
            azioni.append(
                {
                    "index": int(voce["index"]),
                    "stato_precedente": voce["stato_precedente"],
                    "spostamenti": [tuple(s) for s in voce.get("spostamenti", [])],
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return azioni


def clear_state(input_file=INPUT_FILE):
    try:
        os.remove(state_path(input_file))
    except OSError:
        pass


def apply_state(pairs, stato):
    """Applica gli stati salvati alle coppie. Ritorna quante ne ha ritrovate."""
    trovate = 0
    for p in pairs:
        salvato = stato.get((p["a"], p["b"]))
        if salvato:
            p["state"] = salvato
            trovate += 1
    return trovate


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


def restore_from_check_folder(dest, original):
    """Riporta indietro un file spostato. Ritorna True se ci è riuscito.

    Non sovrascrive: se al posto di partenza è nel frattempo comparso un file
    con lo stesso nome, l'annullamento fallisce invece di distruggerlo.
    """
    if not dest or not os.path.exists(dest):
        return False
    if os.path.exists(original):
        return False
    cartella = os.path.dirname(original)
    if cartella:
        os.makedirs(cartella, exist_ok=True)
    shutil.move(dest, original)
    return True


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
