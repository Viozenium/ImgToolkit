import os
import sys

_script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
_local_models = os.path.join(_script_dir, "models")
if os.path.isdir(_local_models) and "HF_HOME" not in os.environ:
    os.environ["HF_HOME"] = _local_models
    os.environ["TORCH_HOME"] = _local_models


def _find_model_path():
    """Cerca il checkpoint scansionando le cache note (nessun hash hardcoded).

    Ordine: $HF_HOME/hub, cache HuggingFace standard, models/ accanto allo script.
    """
    roots = []
    hf_home = os.environ.get("HF_HOME")
    if hf_home:
        roots.append(os.path.join(hf_home, "hub"))
    roots.append(os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub"))
    roots.append(os.path.join(_local_models, "hub"))

    seen = set()
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        if not os.path.isdir(root):
            continue
        for repo in os.listdir(root):
            if "ViT-B-32" not in repo:
                continue
            snapshots = os.path.join(root, repo, "snapshots")
            if not os.path.isdir(snapshots):
                continue
            for commit in os.listdir(snapshots):
                for fname in (
                    "open_clip_model.safetensors",
                    "open_clip_pytorch_model.bin",
                ):
                    candidate = os.path.join(snapshots, commit, fname)
                    if os.path.isfile(candidate):
                        return candidate
    return None


# --------------------------------------------------------------------
# DEVE STARE PRIMA DI QUALSIASI IMPORT CHE TOCCHI HUGGINGFACE.
# Offline solo se il checkpoint è già presente in locale: altrimenti la rete
# resta abilitata, così open_clip può scaricarlo al primo avvio.

_LOCAL_MODEL_PATH = _find_model_path()
if _LOCAL_MODEL_PATH:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import time
import numpy as np
import torch
from PIL import Image, ImageFile
import faiss
import open_clip
from torch.utils.data import Dataset, DataLoader

ImageFile.LOAD_TRUNCATED_IMAGES = True

# --------------------------------------------------------------------
# VALORI PREDEFINITI

DEFAULT_BATCH_SIZE = 128
DEFAULT_SIM_THRESHOLD = 0.95
DEFAULT_OUTPUT_FILE = "Risultati_somiglianza.txt"
CACHE_FILENAME = "embeddings_cache.npz"

VALID_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp")

# --------------------------------------------------------------------
# TETTO DI SICUREZZA PER LA RICERCA
# range_search restituisce TUTTE le coppie sopra soglia, quindi con una soglia
# bassa il totale tende a N². Si cerca a blocchi e ci si ferma superato il
# tetto, invece di esaurire la RAM.

SEARCH_CHUNK = 128
MAX_PAIRS = 2_000_000

device = "cuda" if torch.cuda.is_available() else "cpu"

# --------------------------------------------------------------------
# LIMITE DI THREAD CPU
#
# Senza un tetto torch usa metà dei core logici anche quando non serve, e fra un'operazione e l'altra OpenMP resta in attesa attiva.
# Misurato su 1200imagini con GPU, il default (16 thread) costa 299 secondi-CPU contro i 19 di un solo thread, ed è pure più lento (22,3s contro 19,2s),
# perché con la GPU la parte CPU è preprocessing di un'immagine per volta, che dentro torch non si parallelizza.
#
# Senza GPU il discorso cambia, lì la forward pass gira sui core e il tetto si paga in tempo.
# Su 300 immagini: 11,8s con 16 thread, 18,8s con 4, 27,7s con 1.
# Pur consumando comunque meno energia in totale, da qui i due default.

MAX_CPU_THREADS = 32
DEFAULT_CPU_THREADS_GPU = 1
DEFAULT_CPU_THREADS_CPU = 4


def default_cpu_threads():
    if device == "cuda":
        return DEFAULT_CPU_THREADS_GPU
    return min(DEFAULT_CPU_THREADS_CPU, os.cpu_count() or DEFAULT_CPU_THREADS_CPU)


def set_cpu_threads(n, log=None):
    """Applica il tetto ai thread interni di torch. Ritorna il valore usato."""
    n = max(1, min(MAX_CPU_THREADS, int(n)))
    torch.set_num_threads(n)
    if log:
        log(f"Limite thread CPU: {n} (device: {device})")
    return n

# --------------------------------------------------------------------
# MODELLO (caricato alla prima analisi)

model = None
preprocess = None


def _load_state_manually(model_path, log):
    """Fallback: crea il modello nudo e carica i pesi a mano.
    (Il warning 'initialized randomly' qui è atteso e innocuo:
    i pesi vengono caricati subito dopo.)"""
    m, _, p = open_clip.create_model_and_transforms("ViT-B-32")
    if model_path.endswith(".safetensors"):
        from safetensors.torch import load_file as _load_safetensors

        state = _load_safetensors(model_path, device="cpu")
    else:
        state = torch.load(model_path, map_location="cpu")
    if isinstance(state, dict) and "state_dict" in state:
        state = state["state_dict"]
    missing, unexpected = m.load_state_dict(state, strict=False)
    if missing:
        log(
            f"⚠️    {len(missing)} pesi mancanti nel checkpoint — "
            "risultati potenzialmente errati"
        )
    else:
        log("   → pesi caricati correttamente")
    return m, p


def load_model(log):
    """Carica CLIP dal checkpoint locale, se presente.

    Il percorso locale viene passato come 'pretrained': così open_clip carica
    i pesi direttamente, senza il warning di inizializzazione casuale.
    """
    global model, preprocess
    if model is not None:
        return
    log("Caricamento modello CLIP...")

    model_path = _LOCAL_MODEL_PATH
    if model_path:
        log(f"Modello trovato: {os.path.basename(model_path)}")
        try:
            m, _, p = open_clip.create_model_and_transforms(
                "ViT-B-32", pretrained=model_path
            )
        except Exception as e:
            log(f"   → caricamento diretto non riuscito ({e}), uso metodo manuale")
            m, p = _load_state_manually(model_path, log)
    else:
        log("⬇️    Modello locale non trovato, download in corso (~600MB)...")
        m, _, p = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="laion2b_s34b_b79k"
        )
        log("Download completato.")

    model = m.to(device)
    model.eval()
    preprocess = p
    log(f"Modello caricato su {device.upper()}")


# --------------------------------------------------------------------
# DATASET


class ImageDataset(Dataset):
    def __init__(self, paths, transform):
        self.paths = paths
        self.transform = transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        path = self.paths[idx]
        try:
            img = Image.open(path).convert("RGB")
            return self.transform(img), path
        except Exception:
            return None, path


def collate_skip_broken(batch):
    """Tiene fuori dal batch le immagini illeggibili invece di far fallire tutto."""
    good = [(img, p) for img, p in batch if img is not None]
    bad = [p for img, p in batch if img is None]
    if not good:
        return None, [], bad
    imgs, paths = zip(*good)
    return torch.stack(imgs), list(paths), bad


# --------------------------------------------------------------------
# FUNZIONI PRINCIPALI


def load_images(folder, recursive=False):
    if recursive:
        found = []
        for root, _dirs, files in os.walk(folder):
            for f in files:
                if f.lower().endswith(VALID_EXT):
                    found.append(os.path.join(root, f))
        return sorted(found)
    return sorted(
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(VALID_EXT)
    )


# --------------------------------------------------------------------
# CACHE EMBEDDINGS


def _cache_path(folder):
    return os.path.join(folder, CACHE_FILENAME)


def load_embedding_cache(folder, log):
    """Ritorna dict: relpath -> (mtime, embedding np.array)."""
    p = _cache_path(folder)
    if not os.path.isfile(p):
        return {}
    try:
        data = np.load(p)
        paths = data["paths"]
        mtimes = data["mtimes"]
        embs = data["embeddings"]
        cache = {str(paths[i]): (float(mtimes[i]), embs[i]) for i in range(len(paths))}
        log(f"Cache trovata: {len(cache)} embeddings")
        return cache
    except Exception as e:
        log(f"⚠️    Cache illeggibile ({e}), verrà rigenerata")
        return {}


def save_embedding_cache(folder, cache, log):
    if not cache:
        return
    try:
        paths = np.array(list(cache.keys()))
        mtimes = np.array([v[0] for v in cache.values()], dtype=np.float64)
        embs = np.stack([v[1] for v in cache.values()]).astype(np.float32)
        np.savez_compressed(
            _cache_path(folder), paths=paths, mtimes=mtimes, embeddings=embs
        )
        log(f"Cache salvata ({len(cache)} embeddings)")
    except Exception as e:
        log(f"⚠️    Impossibile salvare la cache: {e}")


def _fmt_eta(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return f"~{seconds}s rimanenti"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"~{m} min {s:02d}s rimanenti"
    h, m = divmod(m, 60)
    return f"~{h}h {m:02d}m rimanenti"


@torch.inference_mode()
def compute_embeddings(
    paths, folder, batch_size, use_cache, stop_event, log, progress_cb
):
    """Ritorna (embeddings, paths) oppure (None, []) se interrotto/vuoto.
    Con use_cache, riusa gli embeddings di immagini invariate e salva
    la cache aggiornata (anche in caso di stop)."""

    cache = load_embedding_cache(folder, log) if use_cache else {}

    def rel(p):
        return os.path.relpath(p, folder)

    reused = {}  # relpath -> emb
    to_compute = []
    for p in paths:
        try:
            mt = os.path.getmtime(p)
        except OSError:
            continue
        r = rel(p)
        if r in cache and abs(cache[r][0] - mt) < 1.0:
            reused[r] = cache[r][1]
        else:
            to_compute.append((p, mt))

    if use_cache and reused:
        log(
            f"   → {len(reused)} embeddings riusati dalla cache, "
            f"{len(to_compute)} da calcolare"
        )

    new_embs = {}  # relpath -> (mtime, emb)
    stopped = False

    if to_compute:
        dataset = ImageDataset([p for p, _ in to_compute], preprocess)
        mtime_by_path = {p: mt for p, mt in to_compute}
        loader = DataLoader(
            dataset,
            batch_size=batch_size,
            num_workers=0,
            shuffle=False,
            collate_fn=collate_skip_broken,
        )
        skipped = []
        total = len(loader)
        use_amp = device == "cuda"
        t0 = time.time()

        for i, (imgs, pths, bad) in enumerate(loader):
            if stop_event.is_set():
                stopped = True
                break
            skipped.extend(bad)
            if imgs is not None:
                imgs = imgs.to(device, non_blocking=True)
                with torch.autocast(device_type="cuda", enabled=use_amp):
                    features = model.encode_image(imgs)
                features = features.float()
                features = features / features.norm(dim=-1, keepdim=True)
                feats = features.cpu().numpy()
                for k, p in enumerate(pths):
                    new_embs[rel(p)] = (mtime_by_path[p], feats[k])

            done = i + 1
            elapsed = time.time() - t0
            eta = (elapsed / done) * (total - done) if done else 0
            progress_cb(int(done / total * 100), _fmt_eta(eta) if done < total else "")

        for p in skipped:
            log(f"⚠️    Immagine saltata (corrotta/illeggibile): {os.path.basename(p)}")
        if skipped:
            log(f"   → {len(skipped)} immagini saltate in totale")
    else:
        progress_cb(100, "")

    # --------------------------------------------------------------------
    # La cache viene salvata anche se l'utente ha interrotto: il lavoro già
    # fatto non va perso.

    if use_cache:
        merged = {r: (cache[r][0], e) for r, e in reused.items()}
        merged.update(new_embs)
        save_embedding_cache(folder, merged, log)

    if stopped:
        return None, []

    all_embs = {}
    all_embs.update(reused)
    all_embs.update({r: e for r, (_, e) in new_embs.items()})
    final_paths, rows = [], []
    for p in paths:
        r = rel(p)
        if r in all_embs:
            final_paths.append(p)
            rows.append(all_embs[r])

    if not rows:
        return None, []
    return np.vstack(rows).astype(np.float32), final_paths


def build_index(embeddings):
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings.astype(np.float32))
    return index


def find_and_save(
    index,
    embeddings,
    paths,
    threshold,
    output_file,
    log,
    max_pairs=MAX_PAIRS,
    stop_event=None,
):
    """Tutte le coppie sopra soglia, senza il tetto arbitrario di top_k.

    La ricerca è fatta a blocchi con un limite sul totale: sotto il tetto i
    risultati sono completi, sopra ci si ferma con un avviso invece di
    esaurire la memoria (range_search alloca tutte le coppie trovate).

    La ricerca è simmetrica, quindi tenendo solo j > i ogni coppia esce una
    volta sola: nessun bisogno di un set di visti, che a milioni di coppie
    costerebbe più dei risultati stessi.
    """
    x = embeddings.astype(np.float32)
    n = len(paths)
    results = []
    truncated = False

    for start in range(0, n, SEARCH_CHUNK):
        if stop_event is not None and stop_event.is_set():
            return []
        end = min(start + SEARCH_CHUNK, n)
        lims, scores, indices = index.range_search(x[start:end], float(threshold))
        for row in range(end - start):
            i = start + row
            for k in range(lims[row], lims[row + 1]):
                j = int(indices[k])
                if j <= i:
                    continue
                results.append((paths[i], paths[j], float(scores[k])))

            # --------------------------------------------------------------------
            # Controllo per riga, non per blocco: un solo blocco può già
            # produrre SEARCH_CHUNK × N coppie e sfondare il tetto.

            if len(results) > max_pairs:
                truncated = True
                break

        if truncated:
            log(
                f"⚠️    Superate {max_pairs:,} coppie: soglia troppo bassa "
                f"({threshold:.2f}). Ricerca interrotta ai primi "
                f"{len(results):,} risultati — alza la soglia."
            )
            break

    results.sort(key=lambda r: -r[2])

    out_dir = os.path.dirname(output_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        for a, b, s in results:
            f.write(f"{a} | {b} | {s:.4f}\n")

    suffix = "  (elenco troncato)" if truncated else ""
    log(f"💾 Salvati {len(results)} risultati in '{output_file}'{suffix}")
    return results


# --------------------------------------------------------------------
# GUI


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Duplicate Finder")
        self.resizable(False, False)
        self.configure(bg="#1a1a2e")

        self._running = False
        self._closing = False
        self._stop_event = threading.Event()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()

    # --------------------------------------------------------------------
    # COSTRUZIONE UI

    def _build_ui(self):
        BG = "#1a1a2e"
        CARD = "#16213e"
        ACCENT = "#0f3460"
        HIGHLIGHT = "#e94560"
        FG = "#eaeaea"
        MUTED = "#8a8fa8"
        FONT_TITLE = ("Courier New", 18, "bold")
        FONT_LABEL = ("Courier New", 10)
        FONT_MONO = ("Courier New", 9)
        ENTRY_BG = "#0d1b2a"

        self._colors = dict(BG=BG, CARD=CARD, ACCENT=ACCENT, HIGHLIGHT=HIGHLIGHT)

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
            font=("Courier New", 11, "bold"),
            bg=HIGHLIGHT,
            fg="#ffffff",
            activebackground="#c73652",
            activeforeground="#ffffff",
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
            font=("Courier New", 11, "bold"),
            bg=ACCENT,
            fg="#ffffff",
            activebackground=HIGHLIGHT,
            activeforeground="#ffffff",
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
        self._run_btn.configure(text="■  STOP", bg="#7b2d42")
        self._set_status("In esecuzione…")

        def finish(status_msg):
            self._running = False
            self._safe_after(
                lambda: self._run_btn.configure(
                    state="normal",
                    text="▶  AVVIA ANALISI",
                    bg=self._colors["HIGHLIGHT"],
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
