"""
Attack Panel - aireplay-ng wrapper.
Deauth attacks and packet injection against targeted APs.
"""

import tkinter as tk
from tkinter import ttk

from core.theme import style_text_widget


class AttackPanel(ttk.Frame):
    def __init__(self, parent, process_manager, get_monitor_iface, get_target):
        super().__init__(parent)
        self.pm = process_manager
        self.get_monitor_iface = get_monitor_iface
        self.get_target = get_target
        self._build_ui()

    def _build_ui(self):
        # Header
        ttk.Label(self, text="Attack (aireplay-ng)", style="Header.TLabel").pack(
            anchor="w", padx=10, pady=(10, 5)
        )

        # Target info (auto-populated from scanner)
        target_frame = ttk.LabelFrame(self, text="Target")
        target_frame.pack(fill="x", padx=10, pady=5)

        row1 = ttk.Frame(target_frame)
        row1.pack(fill="x", padx=5, pady=2)
        ttk.Label(row1, text="BSSID:").pack(side="left")
        self.bssid_var = tk.StringVar()
        self.bssid_entry = ttk.Entry(row1, textvariable=self.bssid_var, width=20)
        self.bssid_entry.pack(side="left", padx=5)

        ttk.Label(row1, text="Channel:").pack(side="left", padx=(10, 0))
        self.channel_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.channel_var, width=6).pack(side="left", padx=5)

        ttk.Button(row1, text="Load from Scanner", command=self._load_target).pack(
            side="right", padx=5
        )

        row2 = ttk.Frame(target_frame)
        row2.pack(fill="x", padx=5, pady=2)
        ttk.Label(row2, text="Client:").pack(side="left")
        self.client_var = tk.StringVar(value="FF:FF:FF:FF:FF:FF")
        ttk.Entry(row2, textvariable=self.client_var, width=20).pack(
            side="left", padx=5
        )
        ttk.Label(row2, text="(broadcast = all clients)").pack(side="left")

        row3 = ttk.Frame(target_frame)
        row3.pack(fill="x", padx=5, pady=2)
        ttk.Label(row3, text="ESSID:").pack(side="left")
        self.essid_var = tk.StringVar()
        ttk.Entry(row3, textvariable=self.essid_var, width=30).pack(
            side="left", padx=5
        )
        ttk.Label(row3, text="(required for fakeauth)").pack(side="left")

        # Attack type
        attack_frame = ttk.LabelFrame(self, text="Attack Type")
        attack_frame.pack(fill="x", padx=10, pady=5)

        self.attack_type = tk.IntVar(value=0)
        attacks = [
            (0, "Deauthentication (--deauth)"),
            (1, "Fake Authentication (--fakeauth)"),
            (3, "ARP Request Replay (--arpreplay)"),
        ]
        for val, label in attacks:
            ttk.Radiobutton(
                attack_frame, text=label, variable=self.attack_type, value=val
            ).pack(anchor="w", padx=10, pady=1)

        # Options
        opt_frame = ttk.Frame(self)
        opt_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(opt_frame, text="Packet count:").pack(side="left")
        self.count_var = tk.StringVar(value="10")
        ttk.Entry(opt_frame, textvariable=self.count_var, width=8).pack(
            side="left", padx=5
        )
        ttk.Label(opt_frame, text="(0 = continuous)").pack(side="left")

        # Action buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=5)

        self.btn_start = ttk.Button(
            btn_frame, text="Launch Attack", command=self._start_attack
        )
        self.btn_start.pack(side="left", padx=2)

        self.btn_stop = ttk.Button(
            btn_frame, text="Stop", command=self._stop_attack, state="disabled"
        )
        self.btn_stop.pack(side="left", padx=2)

        # Log output
        log_frame = ttk.LabelFrame(self, text="Output")
        log_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.log = tk.Text(log_frame, height=12, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=5, pady=5)
        style_text_widget(self.log)

        self._poll_id = None

    def _load_target(self):
        target = self.get_target()
        if target:
            self.bssid_var.set(target["bssid"])
            self.channel_var.set(target["channel"])
            self.essid_var.set(target.get("essid", ""))
            self._log(f"[+] Loaded target: {target['essid']} ({target['bssid']})")
        else:
            self._log("[!] No target selected — right-click an AP in Scanner first")

    def _start_attack(self):
        iface = self.get_monitor_iface()
        if not iface:
            self._log("[!] No monitor interface available")
            return

        bssid = self.bssid_var.get().strip()
        if not bssid:
            self._log("[!] Enter a target BSSID")
            return

        attack = self.attack_type.get()
        count = self.count_var.get().strip() or "10"

        if attack == 0:
            cmd = ["aireplay-ng", "--deauth", count, "-a", bssid]
            client = self.client_var.get().strip()
            if client and client != "FF:FF:FF:FF:FF:FF":
                cmd.extend(["-c", client])
            cmd.append(iface)
        elif attack == 1:
            essid = self.essid_var.get().strip()
            cmd = ["aireplay-ng", "--fakeauth", count, "-a", bssid]
            if essid:
                cmd.extend(["-e", essid])
            cmd.append(iface)
        elif attack == 3:
            cmd = ["aireplay-ng", "--arpreplay", "-b", bssid, iface]
        else:
            self._log(f"[!] Unknown attack type: {attack}")
            return

        self._log(f"\n$ {' '.join(cmd)}")
        self.pm.start("aireplay", cmd)

        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self._start_log_poll()

    def _stop_attack(self):
        self.pm.stop("aireplay")
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self._log("[*] Attack stopped")
        if self._poll_id:
            self.after_cancel(self._poll_id)
            self._poll_id = None

    def _start_log_poll(self):
        """Poll aireplay stdout and display in log."""
        proc = self.pm.get("aireplay")
        if proc and proc.is_running():
            for line in proc.drain_queue():
                self._log(line)
            self._poll_id = self.after(500, self._start_log_poll)
        else:
            # Process ended
            if proc:
                for line in proc.drain_queue():
                    self._log(line)
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
            self._log("[*] aireplay-ng exited")

    def _log(self, text):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.config(state="disabled")
