"""
Scanner Panel - airodump-ng wrapper.
Scans for APs and clients, polls CSV output for live updates.
"""

import tkinter as tk
from tkinter import ttk, filedialog
import os

from core.csv_parser import parse_airodump_csv, find_latest_csv
from core.theme import style_menu


class ScannerPanel(ttk.Frame):
    POLL_INTERVAL_MS = 1500

    def __init__(self, parent, process_manager, get_monitor_iface):
        super().__init__(parent)
        self.pm = process_manager
        self.get_monitor_iface = get_monitor_iface
        self._scan_dir = None
        self._scan_prefix = None
        self._polling = False
        self._selected_ap = None
        self._build_ui()

    def _build_ui(self):
        # --- Controls ---
        ctrl = ttk.Frame(self)
        ctrl.pack(fill="x", padx=10, pady=(10, 5))

        ttk.Label(ctrl, text="Scanner", style="Header.TLabel").pack(side="left")

        btn_frame = ttk.Frame(ctrl)
        btn_frame.pack(side="right")

        self.btn_scan = ttk.Button(btn_frame, text="Start Scan", command=self._start_scan)
        self.btn_scan.pack(side="left", padx=2)

        self.btn_stop = ttk.Button(
            btn_frame, text="Stop Scan", command=self._stop_scan, state="disabled"
        )
        self.btn_stop.pack(side="left", padx=2)

        # Scan options
        opt_frame = ttk.Frame(self)
        opt_frame.pack(fill="x", padx=10, pady=2)

        ttk.Label(opt_frame, text="Channel:").pack(side="left")
        self.channel_var = tk.StringVar(value="all")
        self.channel_entry = ttk.Entry(opt_frame, textvariable=self.channel_var, width=8)
        self.channel_entry.pack(side="left", padx=(2, 10))

        ttk.Label(opt_frame, text="Band:").pack(side="left")
        self.band_var = tk.StringVar(value="abg")
        band_combo = ttk.Combobox(
            opt_frame,
            textvariable=self.band_var,
            values=["abg", "a", "bg"],
            width=6,
            state="readonly",
        )
        band_combo.pack(side="left", padx=2)

        # --- AP Treeview ---
        ap_label = ttk.Label(self, text="Access Points", style="Sub.TLabel")
        ap_label.pack(anchor="w", padx=10, pady=(8, 2))

        ap_frame = ttk.Frame(self)
        ap_frame.pack(fill="both", expand=True, padx=10, pady=2)

        ap_cols = ("bssid", "essid", "channel", "privacy", "power", "beacons", "clients")
        self.ap_tree = ttk.Treeview(ap_frame, columns=ap_cols, show="headings", height=10)

        self.ap_tree.heading("bssid", text="BSSID")
        self.ap_tree.heading("essid", text="ESSID")
        self.ap_tree.heading("channel", text="CH")
        self.ap_tree.heading("privacy", text="Encryption")
        self.ap_tree.heading("power", text="PWR")
        self.ap_tree.heading("beacons", text="Beacons")
        self.ap_tree.heading("clients", text="Clients")

        self.ap_tree.column("bssid", width=150)
        self.ap_tree.column("essid", width=180)
        self.ap_tree.column("channel", width=45)
        self.ap_tree.column("privacy", width=120)
        self.ap_tree.column("power", width=55)
        self.ap_tree.column("beacons", width=70)
        self.ap_tree.column("clients", width=60)

        ap_scroll = ttk.Scrollbar(ap_frame, orient="vertical", command=self.ap_tree.yview)
        self.ap_tree.configure(yscrollcommand=ap_scroll.set)
        self.ap_tree.pack(side="left", fill="both", expand=True)
        ap_scroll.pack(side="right", fill="y")

        # Right-click menu
        self.ap_menu = tk.Menu(self, tearoff=0)
        style_menu(self.ap_menu)
        self.ap_menu.add_command(label="Target this AP", command=self._target_ap)
        self.ap_menu.add_command(label="Copy BSSID", command=self._copy_bssid)
        self.ap_tree.bind("<Button-3>", self._on_ap_right_click)
        self.ap_tree.bind("<Button-2>", self._on_ap_right_click)  # macOS

        # --- Client Treeview ---
        cl_label = ttk.Label(self, text="Clients", style="Sub.TLabel")
        cl_label.pack(anchor="w", padx=10, pady=(8, 2))

        cl_frame = ttk.Frame(self)
        cl_frame.pack(fill="both", expand=True, padx=10, pady=(2, 5))

        cl_cols = ("station", "bssid", "power", "packets", "probed")
        self.cl_tree = ttk.Treeview(cl_frame, columns=cl_cols, show="headings", height=6)

        self.cl_tree.heading("station", text="Station MAC")
        self.cl_tree.heading("bssid", text="AP BSSID")
        self.cl_tree.heading("power", text="PWR")
        self.cl_tree.heading("packets", text="Packets")
        self.cl_tree.heading("probed", text="Probed ESSIDs")

        self.cl_tree.column("station", width=150)
        self.cl_tree.column("bssid", width=150)
        self.cl_tree.column("power", width=55)
        self.cl_tree.column("packets", width=70)
        self.cl_tree.column("probed", width=200)

        cl_scroll = ttk.Scrollbar(cl_frame, orient="vertical", command=self.cl_tree.yview)
        self.cl_tree.configure(yscrollcommand=cl_scroll.set)
        self.cl_tree.pack(side="left", fill="both", expand=True)
        cl_scroll.pack(side="right", fill="y")

        # --- Status bar ---
        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(self, textvariable=self.status_var, relief="sunken").pack(
            fill="x", padx=10, pady=(0, 10)
        )

    def _start_scan(self):
        iface = self.get_monitor_iface()
        if not iface:
            self.status_var.set("No monitor interface — enable monitor mode first")
            return

        # Persistent capture directory
        from datetime import datetime
        from core.logger import get_capture_dir, get_logger
        self._logger = get_logger("scanner")
        base_dir = get_capture_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._scan_dir = os.path.join(base_dir, timestamp)
        os.makedirs(self._scan_dir, exist_ok=True)
        self._scan_prefix = "scan"
        self._logger.info(f"Scan started, captures: {self._scan_dir}")

        cmd = [
            "airodump-ng",
            "--write-interval", "1",
            "-w", os.path.join(self._scan_dir, self._scan_prefix),
            "--output-format", "csv,pcap",
            "--band", self.band_var.get(),
        ]

        ch = self.channel_var.get().strip()
        if ch and ch != "all":
            cmd.extend(["-c", ch])

        cmd.append(iface)

        self.pm.start("airodump", cmd)
        self._polling = True
        self.btn_scan.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.status_var.set(f"Scanning on {iface}...")
        self._poll_csv()

    def _stop_scan(self):
        self._polling = False
        self.pm.stop("airodump")
        self.btn_scan.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.status_var.set("Scan stopped")

    def _poll_csv(self):
        """Periodically re-read the airodump CSV and update treeviews."""
        if not self._polling:
            return

        csv_path = find_latest_csv(self._scan_dir, self._scan_prefix)
        if csv_path:
            aps, clients = parse_airodump_csv(csv_path)
            self._update_ap_tree(aps, clients)
            self._update_client_tree(clients)
            self.status_var.set(
                f"Scanning... {len(aps)} APs, {len(clients)} clients"
            )

        self.after(self.POLL_INTERVAL_MS, self._poll_csv)

    def _update_ap_tree(self, aps, clients):
        """Refresh AP treeview, preserving selection."""
        selected_bssid = None
        sel = self.ap_tree.selection()
        if sel:
            selected_bssid = self.ap_tree.item(sel[0])["values"][0]

        self.ap_tree.delete(*self.ap_tree.get_children())

        # Count clients per AP
        client_counts = {}
        for c in clients:
            bssid = c["bssid"]
            if bssid and bssid != "(not associated)":
                client_counts[bssid] = client_counts.get(bssid, 0) + 1

        for ap in sorted(aps, key=lambda a: a["power"], reverse=True):
            num_clients = client_counts.get(ap["bssid"], 0)
            iid = self.ap_tree.insert(
                "", "end",
                values=(
                    ap["bssid"],
                    ap["essid"],
                    ap["channel"],
                    ap["privacy"],
                    ap["power"],
                    ap["beacons"],
                    num_clients,
                ),
            )
            if ap["bssid"] == selected_bssid:
                self.ap_tree.selection_set(iid)

    def _update_client_tree(self, clients):
        self.cl_tree.delete(*self.cl_tree.get_children())
        for cl in clients:
            self.cl_tree.insert(
                "", "end",
                values=(
                    cl["station"],
                    cl["bssid"],
                    cl["power"],
                    cl["packets"],
                    cl["probed_essids"],
                ),
            )

    def _on_ap_right_click(self, event):
        row = self.ap_tree.identify_row(event.y)
        if row:
            self.ap_tree.selection_set(row)
            self.ap_menu.post(event.x_root, event.y_root)

    def _target_ap(self):
        sel = self.ap_tree.selection()
        if not sel:
            return
        vals = self.ap_tree.item(sel[0])["values"]
        self._selected_ap = {
            "bssid": vals[0],
            "essid": vals[1],
            "channel": vals[2],
        }
        self.status_var.set(f"Targeted: {vals[1]} ({vals[0]}) CH {vals[2]}")

    def _copy_bssid(self):
        sel = self.ap_tree.selection()
        if not sel:
            return
        bssid = self.ap_tree.item(sel[0])["values"][0]
        self.clipboard_clear()
        self.clipboard_append(bssid)

    def get_target(self):
        """Return the currently targeted AP dict, or None."""
        return self._selected_ap

    def get_scan_dir(self):
        """Return the temp dir where captures are stored."""
        return self._scan_dir

    def get_capture_file(self):
        """Find the latest .cap file from the scan."""
        if not self._scan_dir:
            return None
        for f in sorted(os.listdir(self._scan_dir), reverse=True):
            if f.endswith(".cap"):
                return os.path.join(self._scan_dir, f)
        return None
