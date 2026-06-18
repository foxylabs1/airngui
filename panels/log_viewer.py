"""
Log Viewer Panel - displays the application log file.
"""

import tkinter as tk
from tkinter import ttk
import os

from core.logger import LOG_FILE
from core.theme import style_text_widget


class LogPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build_ui()
        self._auto_refresh()

    def _build_ui(self):
        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=(10, 5))

        ttk.Label(header, text="Application Log", style="Header.TLabel").pack(
            side="left"
        )

        btn_frame = ttk.Frame(header)
        btn_frame.pack(side="right")

        ttk.Button(btn_frame, text="Refresh", command=self._load_log).pack(
            side="left", padx=2
        )
        ttk.Button(btn_frame, text="Clear Log", command=self._clear_log).pack(
            side="left", padx=2
        )

        # Log path
        ttk.Label(self, text=LOG_FILE, style="Dim.TLabel").pack(
            anchor="w", padx=10, pady=(0, 5)
        )

        # Log content
        log_frame = ttk.Frame(self)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.log = tk.Text(log_frame, state="disabled", wrap="word")
        style_text_widget(self.log)

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)

        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._load_log()

    def _load_log(self):
        """Read and display the log file."""
        self.log.config(state="normal")
        self.log.delete("1.0", "end")

        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "r") as f:
                    content = f.read()
                self.log.insert("1.0", content)

                # Color error/warning lines
                for i, line in enumerate(content.splitlines(), 1):
                    if "[ERROR]" in line or "ERROR" in line:
                        self.log.tag_add("error", f"{i}.0", f"{i}.end")
                    elif "[WARNING]" in line or "WARNING" in line:
                        self.log.tag_add("warn", f"{i}.0", f"{i}.end")
            except (IOError, OSError):
                self.log.insert("1.0", "[!] Could not read log file")
        else:
            self.log.insert("1.0", "No log file yet. It will appear after the first operation.")

        self.log.see("end")
        self.log.config(state="disabled")

    def _clear_log(self):
        """Clear the log file."""
        try:
            with open(LOG_FILE, "w") as f:
                f.write("")
            self._load_log()
        except (IOError, OSError):
            pass

    def _auto_refresh(self):
        """Auto-refresh log every 5 seconds while panel is visible."""
        if self.winfo_ismapped():
            self._load_log()
        self.after(5000, self._auto_refresh)
