"""Palette e font condivisi da tutte le finestre di ImgToolkit.

Unico posto in cui toccare l'aspetto: prima gli stessi valori erano ripetuti
in cinque file, con il rischio che divergessero al primo ritocco.
"""

# --------------------------------------------------------------------
# COLORI DI BASE

BG = "#1a1a2e"
CARD = "#16213e"
CARD_HOV = "#1e2a50"
ACCENT = "#0f3460"
HIGHLIGHT = "#e94560"
ENTRY_BG = "#0d1b2a"
FG = "#eaeaea"
WHITE = "#ffffff"
MUTED = "#7a7f9a"

# Grigio leggermente più chiaro, usato solo dal Finder.
MUTED_SOFT = "#8a8fa8"

# --------------------------------------------------------------------
# COLORI DEI PULSANTI

HIGHLIGHT_ACT = "#c73652"  # rosso premuto
DANGER = "#7b2d42"  # azioni distruttive / stop
NEUTRAL = "#333355"  # pulsanti secondari
BUSY = "#555555"  # strumento in esecuzione

# --------------------------------------------------------------------
# SCHEDE DEL REVIEWER

TABBAR = "#12122a"
TAB_ACT = "#1a1a2e"
TAB_IDLE = "#0d0d1f"
TAB_HOVER = "#14142a"
DONE_CLR = "#2a4a2a"
SKIP_CLR = "#2a2a1a"
DONE_TAB = "#3a5a3a"
SKIP_TAB = "#3a3a1a"

# --------------------------------------------------------------------
# INDICE DEL MANUALE

NAV_IDLE = "#12122a"
NAV_HOVER = "#1e2a50"
CODE_FG = "#9ad1ff"

# --------------------------------------------------------------------
# FONT

FAMILY = "Courier New"

FONT_XS = (FAMILY, 8)
FONT_MONO = (FAMILY, 9)
FONT_SM = FONT_MONO
FONT = (FAMILY, 10)
FONT_LABEL = FONT
FONT_BOLD = (FAMILY, 10, "bold")
FONT_CARD = (FAMILY, 11, "bold")
FONT_LG = (FAMILY, 13, "bold")
FONT_SECTION = FONT_LG
FONT_HEADER = (FAMILY, 16, "bold")
FONT_TITLE = (FAMILY, 18, "bold")
