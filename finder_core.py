"""Motore del Finder: modello CLIP, embeddings, indice FAISS e ricerca.

Nessuna dipendenza da tkinter: la logica si può usare e misurare senza
aprire una finestra. L'interfaccia sta in finder.py.
"""

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
# Offline solo se il checkpoint è già presente in locale, altrimenti la rete resta abilitata, così open_clip può scaricarlo al primo avvio.

_LOCAL_MODEL_PATH = _find_model_path()
if _LOCAL_MODEL_PATH:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

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
# range_search restituisce TUTTE le coppie sopra soglia, quindi con una soglia bassa il totale tende a N².
# Si cerca a blocchi e ci si ferma superato il tetto, invece di esaurire la RAM.

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
# Su 300 immagini, 11,8s con 16 thread, 18,8s con 4, 27,7s con 1.
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

    reused = {}
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

    new_embs = {}
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
    # La cache viene salvata anche se l'utente ha interrotto, il lavoro già fatto non va perso.

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
            # Controllo per riga, non per blocco, un solo blocco può già produrre SEARCH_CHUNK × N coppie e sfondare il tetto.

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
