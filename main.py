#!/usr/bin/env python3
"""
AirNGUI - GUI for aircrack-ng suite tools.
Must be run as root: sudo python3 main.py
"""

import tkinter as tk
from tkinter import ttk
import os
import sys
import atexit

from core.process import ProcessManager
from core.theme import apply_theme, style_text_widget, style_menu, BG, SIDEBAR_BG, FG, BORDER
from core.logger import setup_logging, LOG_FILE
from panels.interface import InterfacePanel
from panels.scanner import ScannerPanel
from panels.attack import AttackPanel
from panels.cracker import CrackerPanel
from panels.decrypt import DecryptPanel
from panels.log_viewer import LogPanel

APP_NAME = "AirNGUI"
APP_VERSION = "1.0.0"


class AirNGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1050x750")
        self.minsize(850, 600)

        # Apply matrix theme before building widgets
        apply_theme(self)

        # Process manager shared across all panels
        self.pm = ProcessManager()
        atexit.register(self.pm.stop_all)

        self._build_ui()
        self._style_all_text_widgets()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # --- Sidebar ---
        sidebar = tk.Frame(self, bg=SIDEBAR_BG, width=170)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Title
        title_frame = tk.Frame(sidebar, bg=SIDEBAR_BG)
        title_frame.pack(fill="x", padx=10, pady=(15, 5))

        tk.Label(
            title_frame, text="AIR", bg=SIDEBAR_BG, fg=FG,
            font=("Consolas", 18, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_frame, text="NGUI", bg=SIDEBAR_BG, fg="#009926",
            font=("Consolas", 18, "bold"),
        ).pack(anchor="w")

        # Separator
        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", padx=10, pady=10)

        # Nav buttons
        self.nav_buttons = {}
        self._active_nav = None
        panels = [
            ("\u25b8 Interfaces", "interface"),
            ("\u25b8 Scanner",    "scanner"),
            ("\u25b8 Attack",     "attack"),
            ("\u25b8 Cracker",    "cracker"),
            ("\u25b8 Decrypt",    "decrypt"),
            ("\u25b8 Log",        "log"),
        ]

        for label, key in panels:
            btn = tk.Button(
                sidebar, text=label, anchor="w",
                bg=SIDEBAR_BG, fg="#00cc33",
                activebackground="#1a3a1a", activeforeground=FG,
                relief="flat", bd=0, padx=15, pady=8,
                font=("Consolas", 11),
                command=lambda k=key: self._show_panel(k),
            )
            btn.pack(fill="x", padx=5, pady=1)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#0f1f0f"))
            btn.bind("<Leave>", lambda e, b=btn, k=key:
                     b.config(bg="#1a3a1a" if k == self._active_nav else SIDEBAR_BG))
            self.nav_buttons[key] = btn

        # Version at bottom
        tk.Label(
            sidebar, text=f"v{APP_VERSION}", bg=SIDEBAR_BG, fg="#004d1a",
            font=("Consolas", 9),
        ).pack(side="bottom", padx=10, pady=10)

        # --- Separator line ---
        tk.Frame(self, bg=BORDER, width=1).pack(side="left", fill="y")

        # --- Main content area ---
        self.content = ttk.Frame(self)
        self.content.pack(side="right", fill="both", expand=True)

        # Build all panels
        self.panels = {}

        self.panels["interface"] = InterfacePanel(self.content, self.pm)
        self.panels["scanner"] = ScannerPanel(
            self.content, self.pm,
            get_monitor_iface=self.panels["interface"].get_monitor_interface,
        )
        self.panels["attack"] = AttackPanel(
            self.content, self.pm,
            get_monitor_iface=self.panels["interface"].get_monitor_interface,
            get_target=self.panels["scanner"].get_target,
        )
        self.panels["cracker"] = CrackerPanel(
            self.content, self.pm,
            get_capture_file=self.panels["scanner"].get_capture_file,
            get_target=self.panels["scanner"].get_target,
        )
        self.panels["decrypt"] = DecryptPanel(self.content, self.pm)
        self.panels["log"] = LogPanel(self.content)

        # Show first panel
        self._current = None
        self._show_panel("interface")

    def _show_panel(self, key):
        if self._current == key:
            return

        # Update nav button highlighting
        if self._active_nav and self._active_nav in self.nav_buttons:
            self.nav_buttons[self._active_nav].config(bg=SIDEBAR_BG, fg="#00cc33")
        self.nav_buttons[key].config(bg="#1a3a1a", fg=FG)
        self._active_nav = key

        # Hide current
        if self._current:
            self.panels[self._current].pack_forget()
        # Show new
        self.panels[key].pack(fill="both", expand=True)
        self._current = key

    def _style_all_text_widgets(self):
        """Find and style all tk.Text widgets across panels."""
        for panel in self.panels.values():
            for widget in panel.winfo_children():
                self._recursive_style_text(widget)

    def _recursive_style_text(self, widget):
        if isinstance(widget, tk.Text):
            style_text_widget(widget)
        if isinstance(widget, tk.Menu):
            style_menu(widget)
        for child in widget.winfo_children():
            self._recursive_style_text(child)

    def _on_close(self):
        self.pm.stop_all()
        self.destroy()


def check_root():
    if os.geteuid() != 0:
        try:
            root = tk.Tk()
            root.withdraw()
            from tkinter import messagebox
            messagebox.showerror(
                APP_NAME,
                "This application must be run as root.\n\n"
                "Run with: sudo python3 main.py",
            )
            root.destroy()
        except Exception:
            pass
        print(f"[!] {APP_NAME} requires root. Run with: sudo python3 main.py")
        sys.exit(1)


def main():
    check_root()

    logger = setup_logging()
    logger.info(f"Log file: {LOG_FILE}")

    from core.process import run_quick
    retcode, _ = run_quick(["which", "airmon-ng"])
    if retcode != 0:
        logger.error("aircrack-ng suite not found")
        print("[!] aircrack-ng suite not found. Install with:")
        print("    sudo apt install aircrack-ng")
        sys.exit(1)

    try:
        app = AirNGUI()
        app.mainloop()
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
