"""
Interface Panel - airmon-ng wrapper.
List wireless adapters, toggle monitor mode, show status.
"""

import tkinter as tk
from tkinter import ttk
import re

from core.process import run_quick
from core.theme import style_text_widget, style_menu


class InterfacePanel(ttk.Frame):
    def __init__(self, parent, process_manager):
        super().__init__(parent)
        self.pm = process_manager
        self._build_ui()
        self.refresh_interfaces()

    def _build_ui(self):
        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=(10, 5))

        ttk.Label(header, text="Wireless Interfaces", style="Header.TLabel").pack(
            side="left"
        )

        btn_frame = ttk.Frame(header)
        btn_frame.pack(side="right")

        ttk.Button(btn_frame, text="Refresh", command=self.refresh_interfaces).pack(
            side="left", padx=2
        )
        ttk.Button(
            btn_frame, text="Kill Interfering Processes", command=self._check_kill
        ).pack(side="left", padx=2)

        # Interface list
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("interface", "driver", "chipset", "mode")
        self.tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", height=8
        )
        self.tree.heading("interface", text="Interface")
        self.tree.heading("driver", text="Driver")
        self.tree.heading("chipset", text="Chipset")
        self.tree.heading("mode", text="Mode")

        self.tree.column("interface", width=140)
        self.tree.column("driver", width=160)
        self.tree.column("chipset", width=260)
        self.tree.column("mode", width=100)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Update buttons when user clicks a row
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._update_buttons())

        # Action buttons
        action_frame = ttk.Frame(self)
        action_frame.pack(fill="x", padx=10, pady=5)

        self.btn_monitor = ttk.Button(
            action_frame, text="Start Monitor Mode", command=self._toggle_monitor
        )
        self.btn_monitor.pack(side="left", padx=2)

        self.btn_stop = ttk.Button(
            action_frame,
            text="Stop Monitor Mode",
            command=self._stop_monitor,
            state="disabled",
        )
        self.btn_stop.pack(side="left", padx=2)

        # Log output
        log_frame = ttk.LabelFrame(self, text="Output")
        log_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.log = tk.Text(log_frame, height=8, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=5, pady=5)
        style_text_widget(self.log)

    def refresh_interfaces(self):
        """Run airmon-ng (no args) to list interfaces, plus iwconfig for mode."""
        self.tree.delete(*self.tree.get_children())

        # Get mode info from iwconfig
        modes = self._get_interface_modes()

        retcode, output = run_quick(["airmon-ng"])
        self._log(f"$ airmon-ng\n{output}")

        if retcode != 0:
            self._log(f"[ERROR] airmon-ng returned {retcode}")
            return

        # Parse airmon-ng output
        # Typical format:
        # PHY	Interface	Driver		Chipset
        # phy0	wlan0		iwlwifi		Intel ...
        for line in output.splitlines():
            line = line.strip()
            if not line or line.startswith("PHY") or line.startswith("--"):
                continue
            parts = line.split("\t")
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) >= 3:
                # parts: [phy, interface, driver, chipset...]
                iface = parts[1]
                driver = parts[2]
                chipset = parts[3] if len(parts) > 3 else ""
                mode = modes.get(iface, "unknown")
                self.tree.insert("", "end", values=(iface, driver, chipset, mode))

        # Auto-select first item so buttons are always usable
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[0])
            self._update_buttons()

    def _get_interface_modes(self):
        """Use iwconfig to detect managed vs monitor mode per interface."""
        modes = {}
        retcode, output = run_quick(["iwconfig"])
        if retcode != 0:
            return modes

        current_iface = None
        for line in output.splitlines():
            # Interface lines start without whitespace
            if line and not line[0].isspace():
                match = re.match(r"^(\S+)", line)
                if match:
                    current_iface = match.group(1)
            if current_iface and "Mode:" in line:
                mode_match = re.search(r"Mode:(\S+)", line)
                if mode_match:
                    modes[current_iface] = mode_match.group(1).lower()

        return modes

    def _toggle_monitor(self):
        """Start monitor mode on selected interface."""
        selected = self.tree.selection()
        if not selected:
            self._log("[!] Select an interface first")
            return

        iface = self.tree.item(selected[0])["values"][0]

        self._log(f"\n$ airmon-ng start {iface}")
        retcode, output = run_quick(["airmon-ng", "start", iface], timeout=15)
        self._log(output)

        if retcode == 0:
            self._log(f"[+] Monitor mode started on {iface}")
        else:
            self._log(f"[!] Failed (exit code {retcode})")

        self.refresh_interfaces()
        self._update_buttons()

    def _stop_monitor(self):
        """Stop monitor mode and restore managed wifi."""
        selected = self.tree.selection()
        if not selected:
            self._log("[!] Select a monitor interface first")
            return

        iface = self.tree.item(selected[0])["values"][0]

        self._log(f"\n$ airmon-ng stop {iface}")
        retcode, output = run_quick(["airmon-ng", "stop", iface], timeout=15)
        self._log(output)

        # Restart NetworkManager to fully restore managed mode wifi
        self._log("\n[*] Restarting NetworkManager...")
        retcode2, output2 = run_quick(
            ["systemctl", "restart", "NetworkManager"], timeout=15
        )
        if retcode2 == 0:
            self._log("[+] NetworkManager restarted — wifi should reconnect")
        else:
            # Try the older service name
            retcode3, _ = run_quick(
                ["service", "network-manager", "restart"], timeout=15
            )
            if retcode3 == 0:
                self._log("[+] network-manager restarted")
            else:
                self._log("[!] Could not restart NetworkManager — you may need to reconnect manually")

        self.refresh_interfaces()
        self._update_buttons()

    def _check_kill(self):
        """Run airmon-ng check kill to stop interfering processes."""
        self._log("\n$ airmon-ng check kill")
        retcode, output = run_quick(["airmon-ng", "check", "kill"], timeout=10)
        self._log(output)

    def _update_buttons(self):
        """Enable/disable buttons based on selection mode."""
        selected = self.tree.selection()
        if not selected:
            return
        mode = self.tree.item(selected[0])["values"][3]
        if mode == "monitor":
            self.btn_monitor.config(state="disabled")
            self.btn_stop.config(state="normal")
        else:
            self.btn_monitor.config(state="normal")
            self.btn_stop.config(state="disabled")

    def get_monitor_interface(self):
        """Return the first interface in monitor mode, or None."""
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            if values[3] == "monitor":
                return values[0]
        return None

    def _log(self, text):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.config(state="disabled")
