"""
Cracker Panel - aircrack-ng (CPU) and hashcat (GPU) backends.
Select capture file, wordlist, choose backend, run crack with progress.
"""

import tkinter as tk
from tkinter import ttk, filedialog
import re
import os
import subprocess
import threading

from core.process import run_quick
from core.gpu import (
    detect_gpus, check_hashcat, check_hcxtools,
    build_gpu_launch_env, has_discrete_gpu,
)
from core.theme import style_text_widget


class CrackerPanel(ttk.Frame):
    def __init__(self, parent, process_manager, get_capture_file=None, get_target=None):
        super().__init__(parent)
        self.pm = process_manager
        self.get_capture_file = get_capture_file
        self.get_target = get_target
        self._poll_id = None
        self._build_ui()
        self._detect_gpu_status()

    def _build_ui(self):
        ttk.Label(self, text="Cracker", style="Header.TLabel").pack(
            anchor="w", padx=10, pady=(10, 5)
        )

        # --- GPU Status Bar ---
        gpu_frame = ttk.LabelFrame(self, text="GPU Status")
        gpu_frame.pack(fill="x", padx=10, pady=5)

        self.gpu_status_var = tk.StringVar(value="Detecting GPUs...")
        ttk.Label(gpu_frame, textvariable=self.gpu_status_var).pack(
            anchor="w", padx=5, pady=2
        )

        self.hashcat_status_var = tk.StringVar(value="")
        ttk.Label(gpu_frame, textvariable=self.hashcat_status_var,
                  style="Dim.TLabel").pack(anchor="w", padx=5, pady=(0, 2))

        ttk.Button(gpu_frame, text="Refresh GPU", command=self._detect_gpu_status).pack(
            anchor="w", padx=5, pady=(0, 5)
        )

        # --- Backend Selection ---
        backend_frame = ttk.LabelFrame(self, text="Cracking Backend")
        backend_frame.pack(fill="x", padx=10, pady=5)

        self.backend_var = tk.StringVar(value="aircrack")
        ttk.Radiobutton(
            backend_frame, text="aircrack-ng (CPU)", variable=self.backend_var,
            value="aircrack", command=self._on_backend_change,
        ).pack(anchor="w", padx=10, pady=1)
        self.hashcat_radio = ttk.Radiobutton(
            backend_frame, text="hashcat (GPU)", variable=self.backend_var,
            value="hashcat", command=self._on_backend_change,
        )
        self.hashcat_radio.pack(anchor="w", padx=10, pady=1)

        # --- Capture File ---
        cap_frame = ttk.LabelFrame(self, text="Capture File")
        cap_frame.pack(fill="x", padx=10, pady=5)

        cap_row = ttk.Frame(cap_frame)
        cap_row.pack(fill="x", padx=5, pady=5)

        self.cap_var = tk.StringVar()
        ttk.Entry(cap_row, textvariable=self.cap_var, width=50).pack(
            side="left", fill="x", expand=True, padx=(0, 5)
        )
        ttk.Button(cap_row, text="Browse", command=self._browse_cap).pack(side="right")
        ttk.Button(cap_row, text="Load from Scanner", command=self._load_from_scanner).pack(
            side="right", padx=(0, 5)
        )

        # --- Wordlist ---
        wl_frame = ttk.LabelFrame(self, text="Wordlist")
        wl_frame.pack(fill="x", padx=10, pady=5)

        wl_row = ttk.Frame(wl_frame)
        wl_row.pack(fill="x", padx=5, pady=5)

        default_wl = ""
        for path in [
            "/usr/share/wordlists/rockyou.txt",
            "/usr/share/wordlists/rockyou.txt.gz",
        ]:
            if os.path.exists(path):
                default_wl = path
                break

        self.wl_var = tk.StringVar(value=default_wl)
        ttk.Entry(wl_row, textvariable=self.wl_var, width=50).pack(
            side="left", fill="x", expand=True, padx=(0, 5)
        )
        ttk.Button(wl_row, text="Browse", command=self._browse_wl).pack(side="right")

        # --- Options ---
        opt_frame = ttk.Frame(self)
        opt_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(opt_frame, text="BSSID filter:").pack(side="left")
        self.bssid_var = tk.StringVar()
        ttk.Entry(opt_frame, textvariable=self.bssid_var, width=20).pack(
            side="left", padx=5
        )

        self.prime_var = tk.BooleanVar(value=True)
        self.prime_check = ttk.Checkbutton(
            opt_frame, text="PRIME offload (use dGPU)",
            variable=self.prime_var,
        )
        self.prime_check.pack(side="right", padx=5)

        # --- Buttons ---
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=5)

        self.btn_start = ttk.Button(
            btn_frame, text="Start Cracking", command=self._start_crack
        )
        self.btn_start.pack(side="left", padx=2)

        self.btn_stop = ttk.Button(
            btn_frame, text="Stop", command=self._stop_crack, state="disabled"
        )
        self.btn_stop.pack(side="left", padx=2)

        # Progress
        self.progress_var = tk.StringVar(value="Idle")
        ttk.Label(self, textvariable=self.progress_var).pack(
            anchor="w", padx=10, pady=2
        )

        # --- Log ---
        log_frame = ttk.LabelFrame(self, text="Output")
        log_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.log = tk.Text(log_frame, height=12, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=5, pady=5)
        style_text_widget(self.log)

    def _detect_gpu_status(self):
        """Detect GPUs and hashcat availability."""
        gpus = detect_gpus()
        if not gpus:
            self.gpu_status_var.set("No GPUs detected")
        else:
            names = [f"{g.name} ({g.vram_mb}MB)" if g.vram_mb else g.name for g in gpus]
            self.gpu_status_var.set(" | ".join(names))

        hc_ver = check_hashcat()
        hcx = check_hcxtools()

        parts = []
        if hc_ver:
            parts.append(f"hashcat {hc_ver}")
        else:
            parts.append("hashcat: NOT INSTALLED (sudo apt install hashcat)")

        if hcx:
            parts.append("hcxtools: OK")
        else:
            parts.append("hcxtools: NOT INSTALLED (sudo apt install hcxtools)")

        self.hashcat_status_var.set(" | ".join(parts))

        # Disable hashcat radio if not installed
        if not hc_ver:
            self.hashcat_radio.config(state="disabled")
            self.backend_var.set("aircrack")

        # Hide PRIME checkbox if no hybrid GPU setup
        if not has_discrete_gpu():
            self.prime_check.pack_forget()

    def _on_backend_change(self):
        backend = self.backend_var.get()
        if backend == "hashcat":
            self.prime_check.pack(side="right", padx=5)
        else:
            self.prime_check.pack_forget()

    def _browse_cap(self):
        path = filedialog.askopenfilename(
            title="Select capture file",
            filetypes=[
                ("Capture files", "*.cap *.pcap *.pcapng *.hc22000 *.hccapx"),
                ("All", "*.*"),
            ],
        )
        if path:
            self.cap_var.set(path)

    def _browse_wl(self):
        path = filedialog.askopenfilename(
            title="Select wordlist",
            initialdir="/usr/share/wordlists",
            filetypes=[("Text/Wordlists", "*.txt *.lst *.gz"), ("All", "*.*")],
        )
        if path:
            self.wl_var.set(path)

    def _load_from_scanner(self):
        """Load capture file and BSSID from the scanner panel."""
        if self.get_capture_file:
            cap = self.get_capture_file()
            if cap:
                self.cap_var.set(cap)
                self._log(f"[+] Loaded capture: {cap}")
            else:
                self._log("[!] No .cap file found — run a scan first")
                return

        if self.get_target:
            target = self.get_target()
            if target:
                self.bssid_var.set(target["bssid"])
                self._log(f"[+] BSSID filter set: {target['bssid']} ({target.get('essid', '')})")

    def _start_crack(self):
        cap = self.cap_var.get().strip()
        if not cap or not os.path.exists(cap):
            self._log("[!] Select a valid capture file")
            return

        wl = self.wl_var.get().strip()
        if not wl or not os.path.exists(wl):
            self._log("[!] Select a valid wordlist")
            return

        backend = self.backend_var.get()
        if backend == "hashcat":
            self._start_hashcat(cap, wl)
        else:
            self._start_aircrack(cap, wl)

    def _start_aircrack(self, cap, wl):
        cmd = ["aircrack-ng", "-w", wl]
        bssid = self.bssid_var.get().strip()
        if bssid:
            cmd.extend(["-b", bssid])
        cmd.append(cap)

        self._log(f"\n$ {' '.join(cmd)}")
        self.pm.start("aircrack", cmd)

        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.progress_var.set("Cracking (CPU)...")
        self._start_log_poll("aircrack")

    def _start_hashcat(self, cap, wl):
        # Convert .cap to .hc22000 if needed
        if cap.endswith((".cap", ".pcap", ".pcapng")):
            if not check_hcxtools():
                self._log("[!] hcxtools not installed. Install with:")
                self._log("    sudo apt install hcxtools")
                return

            hc_file = cap.rsplit(".", 1)[0] + ".hc22000"
            self._log(f"\n[*] Converting capture to hashcat format...")
            self._log(f"$ hcxpcapngtool -o {hc_file} {cap}")

            retcode, output = run_quick(
                ["hcxpcapngtool", "-o", hc_file, cap], timeout=30
            )
            self._log(output)

            if not os.path.exists(hc_file):
                self._log("[!] Conversion failed — no handshake found in capture?")
                return

            cap = hc_file
            self._log(f"[+] Converted: {hc_file}")

        # Build hashcat command
        # -m 22000 = WPA-PBKDF2-PMKID+EAPOL
        # --status --status-timer=2 for progress updates
        cmd = [
            "hashcat",
            "-m", "22000",
            "-a", "0",  # dictionary attack
            "-D", "2",  # force GPU device type
            "-w", "3",  # workload profile: high performance
            "--status",
            "--status-timer=2",
            cap,
            wl,
        ]

        bssid = self.bssid_var.get().strip()
        # hashcat doesn't filter by BSSID the same way, it's in the hash

        self._log(f"\n$ {' '.join(cmd)}")

        # Use PRIME offload env if enabled
        env = None
        if self.prime_var.get():
            env = build_gpu_launch_env()
            self._log("[*] PRIME offload enabled — using discrete GPU")

        # Launch with custom env via subprocess directly
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            preexec_fn=os.setsid,
        )

        # Wrap in a ManagedProcess-like interface
        from core.process import ManagedProcess
        managed = ManagedProcess("hashcat", cmd)
        managed.proc = proc
        managed._reader_thread = threading.Thread(
            target=managed._read_output, daemon=True
        )
        managed._reader_thread.start()

        self.pm._processes["hashcat"] = managed

        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.progress_var.set("Cracking (GPU)...")
        self._start_log_poll("hashcat")

    def _stop_crack(self):
        for name in ("aircrack", "hashcat"):
            self.pm.stop(name)
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.progress_var.set("Stopped")
        self._log("[*] Cracking stopped")
        if self._poll_id:
            self.after_cancel(self._poll_id)
            self._poll_id = None

    def _start_log_poll(self, proc_name):
        proc = self.pm.get(proc_name)
        if proc and proc.is_running():
            for line in proc.drain_queue():
                self._log(line)
                self._parse_progress(line, proc_name)
            self._poll_id = self.after(300, lambda: self._start_log_poll(proc_name))
        else:
            if proc:
                for line in proc.drain_queue():
                    self._log(line)
                    self._parse_progress(line, proc_name)
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
            if "FOUND" not in self.progress_var.get():
                self.progress_var.set("Finished — key not found")

    def _parse_progress(self, line, backend):
        """Parse output for progress and key found."""
        if backend == "aircrack":
            if "KEY FOUND" in line:
                self.progress_var.set(f"KEY FOUND! {line.strip()}")
                self.log.config(state="normal")
                self.log.insert("end", "\n" + line.strip() + "\n", "found")
                self.log.see("end")
                self.log.config(state="disabled")
                return

            match = re.search(r"(\d+/\d+)\s+keys tested\s+\((.+?)\)", line)
            if match:
                self.progress_var.set(
                    f"Testing: {match.group(1)} @ {match.group(2)}"
                )

        elif backend == "hashcat":
            # Hashcat cracked output
            if "Cracked" in line or "Status" in line:
                self.progress_var.set(line.strip()[:80])

            # Hashcat shows recovered passwords with :<password> format
            if "Speed" in line:
                self.progress_var.set(f"GPU: {line.strip()[:80]}")

            # Check for the actual cracked hash line
            if "::" not in line and ":" in line and "Status" not in line:
                # Could be a cracked result line
                pass

    def set_capture_file(self, path):
        self.cap_var.set(path)

    def set_bssid(self, bssid):
        self.bssid_var.set(bssid)

    def _log(self, text):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.config(state="disabled")
