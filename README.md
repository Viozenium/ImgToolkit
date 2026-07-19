# ImgToolkit

## Italiano

Suite desktop in Python con interfaccia grafica per gestire librerie di immagini su Windows, Linux e macOS.
Trova duplicati/simili tramite embedding CLIP, converte formati, estrae ZIP in blocco e permette la revisione manuale dei doppioni trovati.

### Descrizione

L'applicazione è composta da un launcher e quattro strumenti indipendenti, tutti realizzati con Tkinter, che permettono di:
- Analizzare una cartella di immagini e trovare coppie simili/duplicate tramite embedding CLIP (`open_clip`) e ricerca per similarità con FAISS.
- Rivedere le coppie trovate una per una, con anteprima affiancata, e spostare l'immagine A, la B o entrambe in una cartella dedicata.
- Convertire in blocco immagini PNG, JPEG, BMP, TIFF e WEBP nel formato JPG a qualità massima.
- Decomprimere in blocco tutti i file `.zip` presenti in una cartella, ciascuno nella propria sottocartella.

Il modulo `finder.py` gestisce il caricamento del modello CLIP (locale se già presente, altrimenti scaricato automaticamente al primo avvio) e tutta la pipeline di calcolo degli embedding, in modo separato dagli altri strumenti.

### Funzionalità principali

- Ricerca di immagini simili/duplicate con CLIP ViT-B-32 (`laion2b_s34b_b79k`) + indice FAISS
- Soglia di similarità, batch size e numero di worker regolabili dalla UI
- Revisione manuale a coppie con scorciatoie da tastiera (A / B / S per spostare, N per saltare, frecce per navigare)
- Conversione batch in JPG con selezione dei formati sorgente
- Estrazione batch di archivi ZIP con rilevamento di archivi protetti da password
- Rilevamento automatico GPU (CUDA) con fallback su CPU
- Download automatico del modello CLIP al primo avvio, se non già presente in locale

### Struttura del progetto

```
ImgToolkit/
├── launcher.py     # punto di ingresso, hub per avviare gli altri strumenti
├── finder.py       # ricerca immagini simili/duplicate (CLIP + FAISS)
├── reviewer.py     # revisione manuale delle coppie trovate e spostamento duplicati
├── converter.py    # conversione batch immagini → JPG
├── unzipper.py     # estrazione batch di file .zip
└── info.py         # finestra informazioni / about
```

### Requisiti

1. Python >= 3.10
2. Connessione internet al primo avvio di `finder.py`, per scaricare il checkpoint CLIP (~600MB), se non già presente in cache locale
3. GPU con CUDA opzionale, per accelerare il calcolo degli embedding

#### Librerie necessarie

```
torch
open_clip_torch
faiss-cpu
numpy
Pillow
safetensors
```

`tkinter` è incluso nella libreria standard di Python.

### Utilizzo

```bash
python launcher.py
```

Oppure avviare direttamente il singolo strumento:

```bash
python finder.py
python reviewer.py
python converter.py
python unzipper.py
```

### Note

- `finder.py` cerca il checkpoint CLIP prima nella cache HuggingFace locale, poi in una cartella `models/` accanto allo script; se non lo trova in nessuno dei due, lo scarica automaticamente.
- `reviewer.py` legge i risultati da `Risultati_somiglianza.txt` (generato da `finder.py`) e sposta i duplicati in `~/Desktop/Immagini Duplicate`.
- Il modello CLIP usato (`laion/CLIP-ViT-B-32-laion2B-s34B-b79K`) è rilasciato con licenza MIT; la relativa model card sconsiglia deployment commerciale non testato e vieta esplicitamente usi di sorveglianza/riconoscimento facciale.

---

## English

A Python desktop GUI suite for managing image libraries on Windows, Linux and macOS.
Find duplicate/similar images via CLIP embeddings, convert formats, batch-extract ZIP files, and manually review the matches found.

### Description

The application consists of a launcher and four independent tools, all built with Tkinter, letting the user:
- Scan a folder of images and find similar/duplicate pairs using CLIP embeddings (`open_clip`) and FAISS similarity search.
- Review the found pairs one by one, with a side-by-side preview, and move image A, B, or both to a dedicated folder.
- Batch convert PNG, JPEG, BMP, TIFF and WEBP images to full-quality JPG.
- Batch extract all `.zip` files in a folder, each into its own subfolder.

The `finder.py` module handles loading the CLIP model (from local cache if present, otherwise downloaded automatically on first run) and the whole embedding pipeline, kept separate from the other tools.

### Main features

- Similar/duplicate image search with CLIP ViT-B-32 (`laion2b_s34b_b79k`) + FAISS index
- Adjustable similarity threshold, batch size and worker count from the UI
- Manual pair-by-pair review with keyboard shortcuts (A / B / S to move, N to skip, arrow keys to navigate)
- Batch conversion to JPG with source format selection
- Batch ZIP extraction with password-protected archive detection
- Automatic GPU (CUDA) detection with CPU fallback
- Automatic CLIP model download on first run, if not already available locally

### Requirements

1. Python >= 3.10
2. Internet connection on first run of `finder.py`, to download the CLIP checkpoint (~600MB) if not already cached locally
3. CUDA-capable GPU optional, to speed up embedding computation

#### Required libraries

```
torch
open_clip_torch
faiss-cpu
numpy
Pillow
safetensors
```

`tkinter` is included in Python's standard library.

### Usage

```bash
python launcher.py
```

Or launch a single tool directly:

```bash
python finder.py
python reviewer.py
python converter.py
python unzipper.py
```

---

## Changelog

### v1.0.0
- Prima release pubblica
- `launcher.py` — hub di avvio con card per ciascuno strumento
- `finder.py` — ricerca di immagini duplicate/simili con CLIP ViT-B-32 (open_clip) + indice FAISS, soglia di similarità, batch size e numero di worker regolabili, esportazione risultati su file
- `reviewer.py` — revisione a coppie dei risultati di Finder, spostamento di A, B o entrambe in una cartella dedicata, scorciatoie da tastiera
- `converter.py` — conversione batch di immagini (PNG, JPEG, BMP, TIFF, WEBP) in JPG a qualità massima
- `unzipper.py` — estrazione batch di tutti i file .zip di una cartella, con rilevamento archivi protetti da password
- `info.py` — finestra informazioni/about con link GitHub
