"""
Decrypt Panel - airdecap-ng wrapper.
Decrypt captured traffic using a known key.
"""

import tkinter as tk
from tkinter import ttk, filedialog
import os

from core.process import run_quick
from core.theme import style_text_widget


class DecryptPanel(ttk.Frame):
    def __init__(self, parent, process_manager):
        super().__init__(parent)
        self.pm = process_manager
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Decrypt (airdecap-ng)", style="Header.TLabel").pack(
            anchor="w", padx=10, pady=(10, 5)
        )

        # Capture file
        cap_frame = ttk.LabelFrame(self, text="Capture File")
        cap_frame.pack(fill="x", padx=10, pady=5)

        cap_row = ttk.Frame(cap_frame)
        cap_row.pack(fill="x", padx=5, pady=5)

        self.cap_var = tk.StringVar()
        ttk.Entry(cap_row, textvariable=self.cap_var, width=50).pack(
            side="left", fill="x", expand=True, padx=(0, 5)
        )
        ttk.Button(cap_row, text="Browse", command=self._browse_cap).pack(side="right")

        # Encryption type + key
        key_frame = ttk.LabelFrame(self, text="Decryption Key")
        key_frame.pack(fill="x", padx=10, pady=5)

        type_row = ttk.Frame(key_frame)
        type_row.pack(fill="x", padx=5, pady=5)

        self.enc_type = tk.StringVar(value="wpa")
        ttk.Radiobutton(type_row, text="WPA/WPA2", variable=self.enc_type, value="wpa").pack(
            side="left", padx=5
        )
        ttk.Radiobutton(type_row, text="WEP", variable=self.enc_type, value="wep").pack(
            side="left", padx=5
        )

        key_row = ttk.Frame(key_frame)
        key_row.pack(fill="x", padx=5, pady=5)

        ttk.Label(key_row, text="Key/Passphrase:").pack(side="left")
        self.key_var = tk.StringVar()
        ttk.Entry(key_row, textvariable=self.key_var, width=40).pack(
            side="left", padx=5, fill="x", expand=True
        )

        # ESSID (needed for WPA)
        essid_row = ttk.Frame(key_frame)
        essid_row.pack(fill="x", padx=5, pady=5)

        ttk.Label(essid_row, text="ESSID:").pack(side="left")
        self.essid_var = tk.StringVar()
        ttk.Entry(essid_row, textvariable=self.essid_var, width=30).pack(
            side="left", padx=5
        )
        ttk.Label(essid_row, text="(required for WPA)").pack(side="left")

        # BSSID filter
        bssid_row = ttk.Frame(key_frame)
        bssid_row.pack(fill="x", padx=5, pady=(0, 5))

        ttk.Label(bssid_row, text="BSSID filter:").pack(side="left")
        self.bssid_var = tk.StringVar()
        ttk.Entry(bssid_row, textvariable=self.bssid_var, width=20).pack(
            side="left", padx=5
        )

        # Run button
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(btn_frame, text="Decrypt", command=self._decrypt).pack(
            side="left", padx=2
        )

        # Output
        log_frame = ttk.LabelFrame(self, text="Output")
        log_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.log = tk.Text(log_frame, height=12, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=5, pady=5)
        style_text_widget(self.log)

    def _browse_cap(self):
        path = filedialog.askopenfilename(
            title="Select capture file",
            filetypes=[("Capture files", "*.cap *.pcap *.pcapng"), ("All", "*.*")],
        )
        if path:
            self.cap_var.set(path)

    def _decrypt(self):
        cap = self.cap_var.get().strip()
        if not cap or not os.path.exists(cap):
            self._log("[!] Select a valid capture file")
            return

        key = self.key_var.get().strip()
        if not key:
            self._log("[!] Enter a decryption key")
            return

        enc = self.enc_type.get()
        cmd = ["airdecap-ng"]

        if enc == "wpa":
            essid = self.essid_var.get().strip()
            if not essid:
                self._log("[!] ESSID is required for WPA decryption")
                return
            cmd.extend(["-p", key, "-e", essid])
        else:
            cmd.extend(["-w", key])

        bssid = self.bssid_var.get().strip()
        if bssid:
            cmd.extend(["-b", bssid])

        cmd.append(cap)

        self._log(f"\n$ {' '.join(cmd)}")
        retcode, output = run_quick(cmd, timeout=60)
        self._log(output)

        if retcode == 0:
            # Output file is same name with -dec appended
            dec_file = cap.rsplit(".", 1)[0] + "-dec." + cap.rsplit(".", 1)[-1]
            if os.path.exists(dec_file):
                self._log(f"\n[+] Decrypted file: {dec_file}")
            else:
                self._log("[+] Decryption complete")
        else:
            self._log(f"[!] airdecap-ng exited with code {retcode}")

    def _log(self, text):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.config(state="disabled")
