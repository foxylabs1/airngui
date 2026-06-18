"""
Matrix-style green/black theme for AirNGUI.
"""

# Color palette
BG = "#0a0a0a"
BG_LIGHT = "#141414"
BG_WIDGET = "#1a1a1a"
BG_INPUT = "#111111"
FG = "#00ff41"
FG_DIM = "#00cc33"
FG_DARK = "#009926"
FG_HEADER = "#00ff41"
FG_ACCENT = "#33ff66"
FG_WARN = "#ffcc00"
FG_ERROR = "#ff3333"
FG_FOUND = "#00ff00"
BORDER = "#004d1a"
SELECT_BG = "#003d14"
SELECT_FG = "#00ff41"
TROUGH = "#0d0d0d"
BUTTON_BG = "#1a331a"
BUTTON_ACTIVE = "#264d26"
SIDEBAR_BG = "#050505"
SIDEBAR_BTN = "#0f1f0f"
SIDEBAR_BTN_ACTIVE = "#1a3a1a"


def apply_theme(root):
    """Apply the matrix theme to the entire application."""
    import tkinter.ttk as ttk

    root.configure(bg=BG)

    style = ttk.Style(root)
    style.theme_use("clam")

    # Global defaults
    style.configure(".", background=BG, foreground=FG, fieldbackground=BG_INPUT,
                     bordercolor=BORDER, troughcolor=TROUGH,
                     selectbackground=SELECT_BG, selectforeground=SELECT_FG,
                     font=("Consolas", 10))

    # Frames
    style.configure("TFrame", background=BG)
    style.configure("Sidebar.TFrame", background=SIDEBAR_BG)

    # Labels
    style.configure("TLabel", background=BG, foreground=FG)
    style.configure("Header.TLabel", font=("Consolas", 13, "bold"), foreground=FG_HEADER)
    style.configure("Sub.TLabel", font=("Consolas", 11, "bold"), foreground=FG_ACCENT)
    style.configure("Dim.TLabel", foreground=FG_DARK)
    style.configure("Sidebar.TLabel", background=SIDEBAR_BG, foreground=FG_HEADER,
                     font=("Consolas", 14, "bold"))
    style.configure("SidebarDim.TLabel", background=SIDEBAR_BG, foreground=FG_DARK)

    # Buttons
    style.configure("TButton", background=BUTTON_BG, foreground=FG,
                     bordercolor=BORDER, padding=(8, 4),
                     font=("Consolas", 10))
    style.map("TButton",
              background=[("active", BUTTON_ACTIVE), ("disabled", BG_LIGHT)],
              foreground=[("disabled", FG_DARK)])

    style.configure("Sidebar.TButton", background=SIDEBAR_BTN, foreground=FG_DIM,
                     bordercolor=SIDEBAR_BG, padding=(10, 6),
                     font=("Consolas", 11))
    style.map("Sidebar.TButton",
              background=[("active", SIDEBAR_BTN_ACTIVE)],
              foreground=[("active", FG)])

    # Entry
    style.configure("TEntry", fieldbackground=BG_INPUT, foreground=FG,
                     insertcolor=FG, bordercolor=BORDER)

    # Combobox
    style.configure("TCombobox", fieldbackground=BG_INPUT, foreground=FG,
                     selectbackground=SELECT_BG, selectforeground=SELECT_FG)
    style.map("TCombobox", fieldbackground=[("readonly", BG_INPUT)])
    root.option_add("*TCombobox*Listbox.background", BG_INPUT)
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", SELECT_BG)

    # Treeview
    style.configure("Treeview", background=BG_WIDGET, foreground=FG,
                     fieldbackground=BG_WIDGET, rowheight=24,
                     font=("Consolas", 10))
    style.configure("Treeview.Heading", background=BG_LIGHT, foreground=FG_HEADER,
                     font=("Consolas", 10, "bold"), bordercolor=BORDER)
    style.map("Treeview",
              background=[("selected", SELECT_BG)],
              foreground=[("selected", SELECT_FG)])

    # LabelFrame
    style.configure("TLabelframe", background=BG, foreground=FG, bordercolor=BORDER)
    style.configure("TLabelframe.Label", background=BG, foreground=FG_DIM,
                     font=("Consolas", 10))

    # Radiobutton
    style.configure("TRadiobutton", background=BG, foreground=FG,
                     indicatorcolor=BG_INPUT)
    style.map("TRadiobutton",
              indicatorcolor=[("selected", FG)],
              background=[("active", BG_LIGHT)])

    # Checkbutton
    style.configure("TCheckbutton", background=BG, foreground=FG,
                     indicatorcolor=BG_INPUT)
    style.map("TCheckbutton",
              indicatorcolor=[("selected", FG)],
              background=[("active", BG_LIGHT)])

    # Separator
    style.configure("TSeparator", background=BORDER)

    # Scrollbar
    style.configure("Vertical.TScrollbar", background=BG_LIGHT,
                     troughcolor=TROUGH, bordercolor=BG, arrowcolor=FG_DARK)

    # Notebook (if used later)
    style.configure("TNotebook", background=BG, bordercolor=BORDER)
    style.configure("TNotebook.Tab", background=BG_LIGHT, foreground=FG_DIM,
                     padding=(10, 4))
    style.map("TNotebook.Tab",
              background=[("selected", BG)],
              foreground=[("selected", FG)])

    # Progressbar
    style.configure("green.Horizontal.TProgressbar",
                     troughcolor=TROUGH, background=FG, bordercolor=BORDER)


def style_text_widget(text_widget):
    """Apply matrix colors to a tk.Text widget (not ttk-styled)."""
    text_widget.configure(
        bg=BG_WIDGET,
        fg=FG,
        insertbackground=FG,
        selectbackground=SELECT_BG,
        selectforeground=SELECT_FG,
        font=("Consolas", 10),
        relief="flat",
        highlightbackground=BORDER,
        highlightcolor=BORDER,
        highlightthickness=1,
    )

    # Tags for log highlighting
    text_widget.tag_configure("found", foreground=FG_FOUND, font=("Consolas", 11, "bold"))
    text_widget.tag_configure("warn", foreground=FG_WARN)
    text_widget.tag_configure("error", foreground=FG_ERROR)


def style_menu(menu):
    """Apply matrix colors to a tk.Menu."""
    menu.configure(
        bg=BG_WIDGET,
        fg=FG,
        activebackground=SELECT_BG,
        activeforeground=SELECT_FG,
        relief="flat",
        borderwidth=1,
    )
