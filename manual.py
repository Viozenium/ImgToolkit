import tkinter as tk

try:
    from info import VERSION
except Exception:
    VERSION = "?"

BG = "#1a1a2e"
CARD = "#16213e"
ACCENT = "#0f3460"
HIGHLIGHT = "#e94560"
ENTRY_BG = "#0d1b2a"
FG = "#eaeaea"
MUTED = "#7a7f9a"
NAV_IDLE = "#12122a"
NAV_HOVER = "#1e2a50"
FONT = ("Courier New", 10)
FONT_BOLD = ("Courier New", 10, "bold")
FONT_MONO = ("Courier New", 9)

# --------------------------------------------------------------------
# CONTENUTO DEL MANUALE
#
# Ogni sezione è una lista di blocchi (tag, testo); i tag corrispondono
# agli stili definiti in _configure_tags().

SECTIONS = [
    {
        "key": "panoramica",
        "nav": "Panoramica",
        "title": "PANORAMICA",
        "blocks": [
            (
                "p",
                "ImgToolkit è una suite desktop per gestire librerie di immagini.\n"
                "È composta da un launcher e da tre strumenti indipendenti, più "
                "questo manuale.",
            ),
            ("h2", "Gli strumenti"),
            (
                "li",
                "Finder - analizza una cartella, calcola gli embedding CLIP di "
                "ogni immagine e trova le coppie simili o duplicate.",
            ),
            (
                "li",
                "Reviewer - mostra le coppie trovate una alla volta, affiancate, "
                "e permette di spostare l'immagine A, la B o entrambe.",
            ),
            (
                "li",
                "JPG Converter - converte in blocco immagini PNG, JPEG, BMP, "
                "TIFF e WEBP in formato JPG.",
            ),
            ("li", "Manuale - questa finestra: la guida d'uso completa."),
            ("h2", "Come sono pensati"),
            (
                "p",
                "Ogni strumento è uno script autonomo, può essere avviato dal "
                "launcher oppure direttamente da riga di comando.\n"
                "Finder e Reviewer sono progettati per essere usati in sequenza, perché "
                "il secondo legge il file prodotto dal primo.",
            ),
            (
                "note",
                "Nessuno strumento cancella file, le immagini scartate vengono "
                "spostate, mai eliminate.",
            ),
        ],
    },
    {
        "key": "launcher",
        "nav": "Launcher",
        "title": "LAUNCHER",
        "blocks": [
            (
                "p",
                "Il launcher è la finestra principale, elenca gli strumenti disponibili, ognuno con una scheda e un pulsante «Avvia».",
            ),
            ("h2", "Cosa aspettarsi:"),
            (
                "li",
                "Si può tenere aperto un solo strumento per volta.\n"
                "Mentre è in esecuzione, gli altri pulsanti restano disattivati.",
            ),
            (
                "li",
                "La barra in basso indica lo strumento in esecuzione e segnala "
                "se si è chiuso con un errore.",
            ),
            (
                "li",
                "Chiudendo il launcher mentre uno strumento è aperto viene "
                "chiesta conferma, lo strumento continua a funzionare da solo.",
            ),
            (
                "li",
                "Il pulsante «Info» apre la finestra con versione, autore e link al profilo GitHub.",
            ),
        ],
    },
    {
        "key": "finder",
        "nav": "Finder",
        "title": "FINDER",
        "blocks": [
            (
                "p",
                "Finder analizza una cartella di immagini, ne calcola gli "
                "embedding con il modello CLIP ViT-B-32 e usa un indice FAISS "
                "per trovare tutte le coppie con similarità superiore alla soglia impostata.\n"
                "Il risultato è un file di testo, che verrà poi letto da Reviewer.",
            ),
            ("h2", "Formati letti"),
            ("p", ".jpg · .jpeg · .png · .webp · .bmp"),
            ("h2", "Campi e opzioni"),
            ("li", "Cartella immagini - la cartella da analizzare. Obbligatoria."),
            (
                "li",
                "File output - dove salvare l'elenco delle coppie. "
                "Predefinito: Risultati_somiglianza.txt, creato accanto agli script.",
            ),
            (
                "li",
                "Batch size (1-512, predefinito 128) - quante immagini vengono "
                "elaborate insieme. Se la GPU esaurisce la memoria, abbassalo.",
            ),
            (
                "li",
                "Num workers (0-32, predefinito 6) - processi paralleli che "
                "caricano le immagini da disco. Su Windows, in caso di "
                "problemi, il valore 0 è sempre sicuro.",
            ),
            (
                "li",
                "Usa cache embeddings (attiva) - salva i calcoli in un file "
                "embeddings_cache.npz dentro la cartella analizzata. Le analisi "
                "successive ricalcolano solo le immagini nuove o modificate.",
            ),
            (
                "li",
                "Includi sottocartelle (disattiva) - estende l'analisi a tutte "
                "le sottocartelle.",
            ),
            (
                "li",
                "Soglia similarità (0.50-1.00, predefinita 0.95) - quanto due "
                "immagini devono somigliarsi per finire nell'elenco.",
            ),
            ("h2", "Che soglia usare"),
            (
                "li",
                "0.98-1.00 - praticamente identiche: stesso file, "
                "ricompressioni, ritagli minimi.",
            ),
            (
                "li",
                "0.95 - duplicati veri con piccole differenze: risoluzione, "
                "watermark, filtri leggeri. È il valore consigliato.",
            ),
            (
                "li",
                "0.85-0.92 - immagini somiglianti: stessa scena o stesso "
                "soggetto. Molti più risultati da rivedere a mano.",
            ),
            (
                "li",
                "sotto 0.85 - utile solo per esplorare: il numero di coppie "
                "cresce molto in fretta.",
            ),
            ("h2", "Uso"),
            ("p", "1. Scegli la cartella immagini con «Sfoglia…»."),
            ("p", "2. Se serve, cambia file di output, parametri e soglia."),
            ("p", "3. Premi «AVVIA ANALISI»."),
            (
                "p",
                "4. Segui l'avanzamento nella barra di progresso e nel log; il "
                "tempo stimato compare accanto alla percentuale.",
            ),
            (
                "p",
                "5. A fine analisi le coppie compaiono nella tabella in basso, "
                "ordinate per similarità decrescente e sfogliabili con ◀ e ▶.",
            ),
            (
                "note",
                "Durante l'analisi il pulsante diventa «STOP»: l'interruzione è "
                "pulita e la cache già calcolata viene comunque salvata.",
            ),
            ("h2", "Il modello CLIP"),
            (
                "p",
                "Al primo avvio Finder cerca il checkpoint nella cache locale "
                "di HuggingFace, poi in una cartella models/ accanto agli "
                "script. Se non lo trova, lo scarica automaticamente (~600 MB, "
                "una sola volta). Il caricamento avviene alla prima analisi, "
                "non all'apertura della finestra.",
            ),
            ("h2", "Formato del file di output"),
            ("p", "Una coppia per riga, tre campi separati da « | »:"),
            ("code", "C:\\foto\\a.jpg | C:\\foto\\b.jpg | 0.9817"),
            (
                "note",
                "Con soglie molto basse il numero di coppie può esplodere: "
                "oltre 2.000.000 di risultati la ricerca si ferma e il log lo "
                "segnala. In quel caso alza la soglia.",
            ),
        ],
    },
    {
        "key": "reviewer",
        "nav": "Reviewer",
        "title": "REVIEWER",
        "blocks": [
            (
                "p",
                "Reviewer apre le coppie trovate da Finder e le mostra "
                "affiancate, una alla volta, per decidere quale immagine "
                "tenere.",
            ),
            ("h2", "Prima di aprirlo"),
            (
                "p",
                "Serve il file Risultati_somiglianza.txt nella cartella degli "
                "script: è quello prodotto da Finder. Se manca o è vuoto, "
                "Reviewer lo segnala e si chiude.",
            ),
            ("h2", "La finestra"),
            (
                "li",
                "In alto: il punteggio di similarità della coppia, i nomi dei "
                "due file e lo stato della coppia.",
            ),
            (
                "li",
                "Al centro: le due immagini, A a sinistra e B a destra. Un clic "
                "su un'immagine la apre nel visualizzatore di sistema, a "
                "dimensione piena.",
            ),
            (
                "li",
                "Le schede numerate permettono di saltare a una coppia "
                "qualsiasi: verde = gestita, gialla = saltata.",
            ),
            (
                "li",
                "Il contatore mostra la posizione corrente, le coppie gestite "
                "(✓) e quelle saltate (↷).",
            ),
            ("h2", "Azioni"),
            ("li", "MOVE A - sposta l'immagine di sinistra e passa avanti."),
            ("li", "MOVE B - sposta l'immagine di destra e passa avanti."),
            ("li", "MOVE BOTH - sposta entrambe le immagini."),
            ("li", "SKIP - segna la coppia come saltata senza toccare i file."),
            ("li", "PREV / NEXT - scorre le coppie senza decidere nulla."),
            ("h2", "Dove finiscono le immagini"),
            ("code", "~/Desktop/Immagini Duplicate"),
            (
                "p",
                "La cartella viene creata da sola. I file vengono spostati, non "
                "cancellati: se un nome esiste già viene aggiunto un suffisso "
                "numerico, quindi niente viene mai sovrascritto. Per annullare "
                "una scelta basta riportare il file nella cartella originale.",
            ),
            (
                "note",
                "Dopo l'ultima coppia rimasta, un messaggio conferma che sono "
                "state tutte processate. Se un'immagine è già stata spostata "
                "fuori, l'anteprima mostra un avviso al posto della foto.",
            ),
        ],
    },
    {
        "key": "converter",
        "nav": "JPG Converter",
        "title": "JPG CONVERTER",
        "blocks": [
            (
                "p",
                "Converte in blocco le immagini selezionate in formato JPG, "
                "conservando i metadati EXIF e il profilo colore ICC quando "
                "presenti.",
            ),
            ("h2", "Campi e opzioni"),
            (
                "li",
                "File da convertire - selezione multipla; il filtro del dialogo "
                "mostra solo i formati spuntati.",
            ),
            (
                "li",
                "Cartella destinazione - compilata in automatico con la "
                "cartella dei file scelti; si può cambiare.",
            ),
            (
                "li",
                "Formati da convertire - PNG, JPEG, JPE, BMP, TIFF, WEBP. I "
                "file selezionati ma di formato non spuntato vengono ignorati, "
                "e il log lo indica.",
            ),
            (
                "li",
                "Qualità JPEG (50-100, predefinita 100) - a 95 il risultato è "
                "visivamente identico ma il file pesa circa la metà.",
            ),
            ("h2", "Uso"),
            ("p", "1. Spunta i formati che vuoi convertire."),
            ("p", "2. Scegli i file con «Sfoglia…»."),
            ("p", "3. Controlla la cartella di destinazione e la qualità."),
            ("p", "4. Premi «Converti» e segui il log."),
            ("h2", "Dettagli utili"),
            (
                "li",
                "Le trasparenze (PNG, WEBP) vengono appiattite su fondo bianco, "
                "non nero.",
            ),
            (
                "li",
                "L'orientamento EXIF viene applicato, quindi le foto ruotate "
                "restano dritte.",
            ),
            (
                "li",
                "Se esiste già un file con lo stesso nome, il nuovo viene "
                "salvato come nome_1.jpg, nome_2.jpg e così via: gli originali "
                "non vengono mai toccati né sovrascritti.",
            ),
        ],
    },
    {
        "key": "flusso",
        "nav": "Flusso di lavoro",
        "title": "FLUSSO DI LAVORO CONSIGLIATO",
        "blocks": [
            (
                "p",
                "Per ripulire una libreria dai duplicati, l'ordine più comodo è "
                "questo:",
            ),
            (
                "p",
                "1. Se la cartella contiene formati misti, passa prima da JPG "
                "Converter per uniformare (facoltativo).",
            ),
            (
                "p",
                "2. Apri Finder, punta alla cartella, lascia la soglia a 0.95 e "
                "avvia l'analisi.",
            ),
            (
                "p",
                "3. Guarda quante coppie sono uscite: troppe poche, abbassa la "
                "soglia; troppe, alzala e rilancia. Con la cache attiva la "
                "seconda analisi è quasi immediata.",
            ),
            (
                "p",
                "4. Apri Reviewer e passa in rassegna le coppie: parti da "
                "quelle con punteggio più alto, sono le più sicure.",
            ),
            (
                "p",
                "5. Controlla la cartella «Immagini Duplicate» sul Desktop "
                "prima di eliminarne il contenuto a mano.",
            ),
            (
                "note",
                "Reviewer legge il file una sola volta, all'apertura: se "
                "rilanci Finder, riavvia anche Reviewer per vedere i nuovi "
                "risultati.",
            ),
        ],
    },
    {
        "key": "scorciatoie",
        "nav": "Scorciatoie",
        "title": "SCORCIATOIE DA TASTIERA",
        "blocks": [
            ("h2", "Reviewer"),
            ("kv", "A|sposta l'immagine A e passa avanti"),
            ("kv", "B|sposta l'immagine B e passa avanti"),
            ("kv", "S|sposta entrambe le immagini"),
            ("kv", "N|salta la coppia"),
            ("kv", "← →|coppia precedente / successiva"),
            ("kv", "Q|chiude la finestra"),
            ("kv", "clic|apre l'immagine nel visualizzatore di sistema"),
            ("h2", "Manuale"),
            ("kv", "↑ ↓|scorre il testo"),
            ("kv", "Pag↑ Pag↓|scorre di una schermata"),
            ("kv", "Home Fine|inizio / fine del manuale"),
            ("kv", "Esc|chiude la finestra"),
        ],
    },
    {
        "key": "problemi",
        "nav": "Problemi frequenti",
        "title": "PROBLEMI FREQUENTI",
        "blocks": [
            ("h2", "Finder resta fermo al primo avvio"),
            (
                "p",
                "Sta scaricando il modello CLIP (~600 MB). Succede una sola "
                "volta: dalle analisi successive il caricamento è rapido.",
            ),
            ("h2", "Errore di memoria sulla GPU"),
            (
                "p",
                "Abbassa il Batch size (per esempio a 32 o 16). Senza GPU il "
                "programma funziona comunque, solo più lentamente.",
            ),
            ("h2", "L'analisi si blocca o è lentissima su Windows"),
            (
                "p",
                "Prova Num workers a 0: il caricamento delle immagini avviene "
                "nel processo principale, senza sottoprocessi.",
            ),
            ("h2", "Reviewer dice che il file non esiste"),
            (
                "p",
                "Va eseguito Finder prima, e Reviewer va avviato dalla stessa "
                "cartella in cui è stato salvato Risultati_somiglianza.txt.",
            ),
            ("h2", "Troppe coppie da rivedere"),
            (
                "p",
                "Alza la soglia di similarità e ripeti l'analisi: con la cache "
                "attiva non servono nuovi calcoli, solo la ricerca.",
            ),
            ("h2", "Ho spostato l'immagine sbagliata"),
            (
                "p",
                "Niente è perduto: i file spostati sono in ~/Desktop/Immagini "
                "Duplicate; basta riportarli indietro.",
            ),
            ("h2", "Il launcher in versione .exe non avvia gli strumenti"),
            (
                "p",
                "In versione compilata il launcher non può lanciare gli script "
                "con l'interprete Python: avviali direttamente da riga di "
                "comando.",
            ),
            ("h2", "La cache occupa spazio"),
            (
                "p",
                "Il file embeddings_cache.npz si trova nella cartella "
                "analizzata e si può cancellare in qualsiasi momento: verrà "
                "ricalcolato alla prossima analisi.",
            ),
        ],
    },
    {
        "key": "info",
        "nav": "Note e licenza",
        "title": "NOTE E LICENZA",
        "blocks": [
            ("h2", "File prodotti dagli strumenti"),
            ("kv", "Risultati_somiglianza.txt|elenco delle coppie trovate da Finder"),
            ("kv", "embeddings_cache.npz|cache degli embedding, nella cartella analizzata"),
            ("kv", "Immagini Duplicate|cartella sul Desktop con le immagini spostate"),
            ("h2", "Modello e licenze"),
            (
                "p",
                "ImgToolkit è distribuito con licenza MIT. Il modello usato è "
                "laion/CLIP-ViT-B-32-laion2B-s34B-b79K, anch'esso MIT: la sua "
                "model card sconsiglia impieghi commerciali non verificati e "
                "vieta esplicitamente usi di sorveglianza o riconoscimento "
                "facciale.",
            ),
            ("h2", "Privacy"),
            (
                "p",
                "Le immagini non lasciano mai il computer: l'unica connessione "
                "di rete è il download iniziale del modello.",
            ),
        ],
    },
]


# --------------------------------------------------------------------
# RENDERING DEL TESTO


def _configure_tags(txt):
    txt.tag_configure(
        "title",
        font=("Courier New", 13, "bold"),
        foreground=HIGHLIGHT,
        spacing1=18,
        spacing3=8,
    )
    txt.tag_configure("h2", font=FONT_BOLD, foreground=FG, spacing1=12, spacing3=4)
    txt.tag_configure("p", font=FONT, foreground=FG, spacing3=6)
    txt.tag_configure(
        "li", font=FONT, foreground=FG, spacing3=4, lmargin1=14, lmargin2=30
    )
    txt.tag_configure(
        "note",
        font=FONT_MONO,
        foreground=MUTED,
        spacing1=6,
        spacing3=8,
        lmargin1=14,
        lmargin2=28,
    )
    txt.tag_configure(
        "code",
        font=FONT_MONO,
        foreground="#9ad1ff",
        background=ENTRY_BG,
        spacing1=6,
        spacing3=8,
        lmargin1=14,
        lmargin2=14,
        rmargin=14,
    )
    txt.tag_configure(
        "kv", font=FONT, foreground=FG, spacing3=4, lmargin1=14, lmargin2=42
    )
    txt.tag_configure("key", font=FONT_BOLD, foreground=HIGHLIGHT)
    txt.tag_configure("rule", font=FONT_MONO, foreground=ACCENT, spacing3=6)


def _render(txt, sections):
    """Scrive tutte le sezioni e ritorna {key: nome del mark} per l'indice."""
    marks = {}
    txt.config(state="normal")
    txt.delete("1.0", "end")
    for i, section in enumerate(sections, start=1):
        mark = f"sec_{section['key']}"
        txt.mark_set(mark, "end-1c")
        txt.mark_gravity(mark, "left")
        marks[section["key"]] = mark
        txt.insert("end", f"{i} · {section['title']}\n", "title")
        txt.insert("end", "─" * 56 + "\n", "rule")
        for tag, text in section["blocks"]:
            if tag == "li":
                txt.insert("end", "• " + text + "\n", "li")
            elif tag == "kv":
                key, _, desc = text.partition("|")
                txt.insert("end", f"{key:<12}", ("kv", "key"))
                txt.insert("end", f"  {desc}\n", "kv")
            elif tag == "note":
                txt.insert("end", "↳ " + text + "\n", "note")
            else:
                txt.insert("end", text + "\n", tag)

    # Coda vuota: permette di portare in cima anche l'ultima sezione.
    txt.insert("end", "\n" * 24, "p")
    txt.config(state="disabled")
    return marks


# --------------------------------------------------------------------
# GUI


def manual_main(parent, standalone=False):
    root = tk.Toplevel(parent)
    root.title("Manuale d'uso")
    root.geometry("900x640")
    root.minsize(780, 520)
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
    root.bind("<Escape>", lambda e: safe_exit())

    # --------------------------------------------------------------------
    # Barra del titolo

    tk.Frame(root, bg=HIGHLIGHT, height=3).pack(fill="x")
    hdr = tk.Frame(root, bg=BG, padx=28, pady=16)
    hdr.pack(fill="x")
    tk.Label(
        hdr,
        text="◈  MANUALE D'USO",
        font=("Courier New", 16, "bold"),
        bg=BG,
        fg=HIGHLIGHT,
    ).pack(anchor="w")
    tk.Label(
        hdr,
        text=f"Guida agli strumenti di ImgToolkit  ·  v{VERSION}",
        font=FONT,
        bg=BG,
        fg=MUTED,
    ).pack(anchor="w")
    tk.Frame(root, bg=HIGHLIGHT, height=1).pack(fill="x")

    # --------------------------------------------------------------------
    # Barra azioni (ancorata in basso, prima del corpo)

    tk.Frame(root, bg=ACCENT, height=1).pack(fill="x", side="bottom")
    bar = tk.Frame(root, bg=BG, height=60)
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
        bg=HIGHLIGHT,
        fg=FG,
        activebackground="#c73652",
        activeforeground=FG,
        relief="flat",
        bd=0,
        padx=16,
        pady=8,
        command=safe_exit,
    ).pack(side="right", padx=(8, 28), pady=11)

    # --------------------------------------------------------------------
    # Corpo: indice a sinistra, testo a destra

    body = tk.Frame(root, bg=BG, padx=24, pady=16)
    body.pack(fill="both", expand=True)

    nav = tk.Frame(body, bg=CARD, padx=8, pady=10)
    nav.pack(side="left", fill="y", padx=(0, 16))
    tk.Label(nav, text="INDICE", font=FONT_MONO, bg=CARD, fg=MUTED, anchor="w").pack(
        fill="x", padx=6, pady=(0, 6)
    )

    text_wrap = tk.Frame(body, bg=CARD)
    text_wrap.pack(side="left", fill="both", expand=True)

    txt = tk.Text(
        text_wrap,
        font=FONT,
        bg=CARD,
        fg=FG,
        insertbackground=CARD,
        relief="flat",
        bd=0,
        padx=20,
        pady=10,
        wrap="word",
        cursor="arrow",
        state="disabled",
    )
    sb = tk.Scrollbar(text_wrap, command=txt.yview, bg=CARD)
    txt.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    txt.pack(fill="both", expand=True)

    _configure_tags(txt)
    marks = _render(txt, SECTIONS)

    # --------------------------------------------------------------------
    # Indice navigabile

    nav_buttons = {}
    active_key = [None]

    def highlight(key):
        """Evidenzia una voce dell'indice, ignorando le chiamate ridondanti."""
        if key == active_key[0] or key not in nav_buttons:
            return
        active_key[0] = key
        for k, b in nav_buttons.items():
            active = k == key
            b.configure(bg=ACCENT if active else NAV_IDLE, fg=FG if active else MUTED)
        status_var.set(f"Sezione: {next(s for s in SECTIONS if s['key'] == key)['nav']}")

    def visible_key():
        """Sezione a cui appartiene la prima riga visibile del testo."""
        top = txt.index("@0,0")
        key = SECTIONS[0]["key"]
        for section in SECTIONS:
            if txt.compare(marks[section["key"]], "<=", top):
                key = section["key"]
            else:
                break
        return key

    def on_yscroll(first, last):
        """Aggiorna la scrollbar e segue lo scorrimento nell'indice."""
        sb.set(first, last)
        highlight(visible_key())

    txt.configure(yscrollcommand=on_yscroll)

    def goto(section):
        txt.yview(marks[section["key"]])
        highlight(section["key"])

    for i, section in enumerate(SECTIONS, start=1):
        b = tk.Button(
            nav,
            text=f"{i:>2}. {section['nav']}",
            font=FONT_MONO,
            bg=NAV_IDLE,
            fg=MUTED,
            activebackground=HIGHLIGHT,
            activeforeground=FG,
            relief="flat",
            bd=0,
            anchor="w",
            padx=10,
            pady=6,
            width=20,
            cursor="hand2",
            command=lambda s=section: goto(s),
        )
        b.pack(fill="x", pady=1)
        nav_buttons[section["key"]] = b

        def on_enter(_e, btn=b):
            if btn.cget("bg") != ACCENT:
                btn.configure(bg=NAV_HOVER)

        def on_leave(_e, btn=b):
            if btn.cget("bg") != ACCENT:
                btn.configure(bg=NAV_IDLE)

        b.bind("<Enter>", on_enter)
        b.bind("<Leave>", on_leave)

    goto(SECTIONS[0])

    # --------------------------------------------------------------------
    # Scorrimento con rotella e tastiera

    def on_wheel(event):
        if event.num == 4:
            txt.yview_scroll(-3, "units")
        elif event.num == 5:
            txt.yview_scroll(3, "units")
        else:
            txt.yview_scroll(int(-1 * (event.delta / 40)), "units")
        return "break"

    for widget in (txt, nav, body):
        widget.bind("<MouseWheel>", on_wheel)
        widget.bind("<Button-4>", on_wheel)
        widget.bind("<Button-5>", on_wheel)

    root.bind("<Up>", lambda e: txt.yview_scroll(-2, "units"))
    root.bind("<Down>", lambda e: txt.yview_scroll(2, "units"))
    root.bind("<Prior>", lambda e: txt.yview_scroll(-1, "pages"))
    root.bind("<Next>", lambda e: txt.yview_scroll(1, "pages"))
    root.bind("<Home>", lambda e: txt.yview_moveto(0))
    root.bind("<End>", lambda e: txt.yview_moveto(1))
    txt.focus_set()

    return root


# --------------------------------------------------------------------
# AVVIO AUTONOMO

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    manual_main(root, standalone=True)
    root.mainloop()
