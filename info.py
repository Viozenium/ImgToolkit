import tkinter as tk
import webbrowser

from theme import (
    BG,
    ACCENT,
    HIGHLIGHT,
    HIGHLIGHT_ACT,
    FG,
    MUTED,
    FONT,
    FONT_BOLD,
    FONT_HEADER,
)

VERSION = "1.1.2"
AUTHOR = "Mizu"
GITHUB_USER = "Viozenium"
GITHUB_URL = f"https://github.com/{GITHUB_USER}"


def main(parent=None):
    standalone = parent is None
    if standalone:
        info_win = tk.Tk()
    else:
        info_win = tk.Toplevel(parent)

    info_win.title("Info")
    info_win.geometry("360x260")
    info_win.resizable(False, False)
    info_win.configure(bg=BG)

    def close():
        if not standalone:
            try:
                info_win.grab_release()
            except tk.TclError:
                pass
        info_win.destroy()

    info_win.protocol("WM_DELETE_WINDOW", close)
    info_win.bind("<Escape>", lambda e: close())

    if not standalone:
        info_win.wait_visibility()
        info_win.grab_set()
        info_win.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - info_win.winfo_width()) // 2
        py = (
            parent.winfo_rooty()
            + (parent.winfo_height() - info_win.winfo_height()) // 2
        )
        info_win.geometry(f"+{max(0, px)}+{max(0, py)}")
    tk.Frame(info_win, bg=HIGHLIGHT, height=3).pack(fill="x")
    hdr = tk.Frame(info_win, bg=BG, padx=28, pady=18)
    hdr.pack(fill="x")
    tk.Label(hdr, text="◈  ABOUT", font=FONT_HEADER, bg=BG, fg=HIGHLIGHT).pack(
        anchor="w"
    )
    tk.Frame(info_win, bg=ACCENT, height=1).pack(fill="x", padx=28)
    body = tk.Frame(info_win, bg=BG, padx=28, pady=20)
    body.pack(fill="both", expand=True)

    def row(label, value):
        f = tk.Frame(body, bg=BG)
        f.pack(fill="x", pady=5)
        tk.Label(
            f,
            text=label,
            font=FONT,
            bg=BG,
            fg=MUTED,
            width=10,
            anchor="w",
        ).pack(side="left")
        tk.Label(f, text=value, font=FONT_BOLD, bg=BG, fg=FG, anchor="w").pack(
            side="left"
        )

    row("Author", AUTHOR)
    row("Version", VERSION)
    f = tk.Frame(body, bg=BG)
    f.pack(fill="x", pady=5)
    tk.Label(
        f,
        text="GitHub",
        font=FONT,
        bg=BG,
        fg=MUTED,
        width=10,
        anchor="w",
    ).pack(side="left")
    link = tk.Label(
        f,
        text=GITHUB_USER,
        font=FONT_BOLD,
        bg=BG,
        fg=HIGHLIGHT,
        cursor="hand2",
        anchor="w",
    )
    link.pack(side="left")
    link.bind("<Button-1>", lambda e: webbrowser.open(GITHUB_URL))
    link.bind("<Enter>", lambda e: link.config(fg=FG))
    link.bind("<Leave>", lambda e: link.config(fg=HIGHLIGHT))
    tk.Frame(info_win, bg=ACCENT, height=1).pack(fill="x")
    tk.Button(
        info_win,
        text="Chiudi",
        font=FONT_BOLD,
        bg=HIGHLIGHT,
        fg=FG,
        activebackground=HIGHLIGHT_ACT,
        activeforeground=FG,
        relief="flat",
        bd=0,
        padx=20,
        pady=8,
        command=close,
    ).pack(pady=12)

    if standalone:
        info_win.mainloop()

    return info_win


if __name__ == "__main__":
    main()
