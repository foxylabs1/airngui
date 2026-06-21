# AirNGUI

A graphical interface for the aircrack-ng wireless security toolkit with GPU-accelerated cracking via hashcat.

Built for Debian-based Linux systems with NVIDIA hybrid GPU support.

![Python](https://img.shields.io/badge/Python-3.10+-green)
![Platform](https://img.shields.io/badge/Platform-Debian%20%7C%20Kali-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Features

**Interface Management** — List wireless adapters, toggle monitor mode on/off, kill interfering processes. Detects interface mode via iwconfig and auto-refreshes after changes. Restarts NetworkManager when stopping monitor mode to restore wifi connectivity.

**Network Scanner** — Live scanning powered by airodump-ng with CSV polling. Sortable tables for access points (BSSID, ESSID, channel, encryption, signal strength, client count) and associated clients. Right-click to target an AP for attacks. Writes both CSV and pcap capture files.

**Attack Panel** — Deauthentication, fake authentication, and ARP replay attacks via aireplay-ng. Auto-loads target BSSID and channel from the scanner. Supports targeted client deauth for more reliable handshake capture.

**Cracker** — Dual backend: aircrack-ng (CPU) and hashcat (GPU). Automatic .cap to .hc22000 conversion via hcxpcapngtool. NVIDIA PRIME render offload for hybrid GPU laptops ensures hashcat runs on the discrete GPU. GPU detection via nvidia-smi and lspci. Progress parsing and key-found highlighting.

**Decrypt** — Decrypt captured WPA/WPA2 and WEP traffic using airdecap-ng with a known key.

**Application Log** — Built-in log viewer with auto-refresh. Color-coded errors (red) and warnings (yellow). Log file persists at `~/.local/share/airngui/airngui.log`.

**Matrix Theme** — Green-on-black terminal aesthetic using Consolas monospace throughout. Styled treeviews, inputs, buttons, scrollbars, and context menus.

---

## Requirements

- Debian 13 (Trixie), Kali Linux, or any Debian-based distribution
- Python 3.10+
- Wireless adapter capable of monitor mode and packet injection
- Root access (required by aircrack-ng tools)

### Dependencies (auto-installed with .deb)

- `python3-tk` — GUI framework
- `aircrack-ng` — Wireless security suite
- `wireless-tools` — iwconfig and related tools
- `hashcat` — GPU-accelerated password cracking
- `hcxtools` — Capture file conversion (cap to hc22000)
- `zenity` — Graphical sudo password prompt

### Optional

- `nvidia-driver` + `nvidia-cuda-toolkit` — For GPU cracking on NVIDIA cards
- `nvidia-opencl-icd` — OpenCL fallback for NVIDIA GPUs

---

## Installation

### From .deb package (recommended)

```bash
sudo apt install ./airngui_1.0.3_all.deb
```

This installs the application, all dependencies, a desktop launcher, and the `airngui` command.

### From source

```bash
git clone https://github.com/youruser/airngui.git
cd airngui
sudo apt install python3-tk aircrack-ng wireless-tools hashcat hcxtools zenity
sudo python3 main.py
```

---

## Usage

### Launch

From terminal:
```bash
airngui
```

From the application menu: find AirNGUI under Network or Security. A password dialog will prompt for root access.

### Typical Workflow

1. **Interfaces** — Select your wireless adapter and click "Start Monitor Mode"
2. **Scanner** — Click "Start Scan" to discover nearby networks. Right-click a target AP and select "Target this AP"
3. **Attack** — Click "Load from Scanner" to populate the target. Enter the client MAC for targeted deauth (or leave as broadcast). Set packet count and click "Launch Attack"
4. **Scanner** — Verify handshake was captured (check packet counts increasing during reconnection)
5. **Cracker** — Click "Load from Scanner" to pull the capture file. Select a wordlist (defaults to rockyou.txt). Choose aircrack-ng (CPU) or hashcat (GPU) and click "Start Cracking"

### GPU Cracking Setup

For NVIDIA hybrid GPU laptops (Intel iGPU + NVIDIA dGPU):

```bash
sudo apt install nvidia-driver nvidia-cuda-toolkit nvidia-opencl-icd
```

AirNGUI automatically detects the GPU and applies PRIME render offload so hashcat runs on the discrete GPU. The "PRIME offload" checkbox in the Cracker panel controls this behavior.

Verify GPU detection:
```bash
hashcat -I
```

---

## File Locations

| Path | Contents |
|------|----------|
| `/opt/airngui/` | Application files |
| `/usr/local/bin/airngui` | Launcher script |
| `/usr/share/applications/airngui.desktop` | Desktop entry |
| `~/airngui-captures/` | Saved capture files (persistent) |
| `~/.local/share/airngui/airngui.log` | Application log |

---

## Project Structure

```
airngui/
├── main.py                 # Entry point, root check, main window
├── core/
│   ├── process.py          # Subprocess manager for aircrack-ng tools
│   ├── csv_parser.py       # Airodump-ng CSV output parser
│   ├── gpu.py              # GPU detection and PRIME offload
│   ├── theme.py            # Matrix green/black theme
│   └── logger.py           # File logging setup
├── panels/
│   ├── interface.py        # airmon-ng panel
│   ├── scanner.py          # airodump-ng panel
│   ├── attack.py           # aireplay-ng panel
│   ├── cracker.py          # aircrack-ng + hashcat panel
│   ├── decrypt.py          # airdecap-ng panel
│   └── log_viewer.py       # Log file viewer
└── askpass.sh              # Zenity password prompt for sudo
```

---

## Uninstall

```bash
sudo apt remove airngui
```

Capture files in `~/airngui-captures/` and logs in `~/.local/share/airngui/` are preserved after uninstall.

---

## Troubleshooting

**"No monitor interface" error** — Go to the Interfaces tab and start monitor mode first. Your wireless adapter must support monitor mode and packet injection.

**Hashcat using CPU instead of GPU** — Install `nvidia-opencl-icd` or `nvidia-cuda-toolkit`. Run `hashcat -I` to verify the GPU is detected. Make sure the "PRIME offload" checkbox is enabled in the Cracker panel.

**Scanner shows no networks** — Ensure monitor mode is active. Try "Kill Interfering Processes" in the Interfaces tab. Some adapters need specific channels — set the channel manually instead of scanning all.

**App won't launch from menu** — Check that zenity is installed: `sudo apt install zenity`. Check the log at `/root/.local/share/airngui/airngui.log` for errors.

**Wifi doesn't reconnect after stopping monitor mode** — The app restarts NetworkManager automatically, but if it fails: `sudo systemctl restart NetworkManager`

---

## Legal

This tool is intended for authorized security testing and educational purposes only. Unauthorized access to computer networks is illegal. Always obtain explicit permission before testing any network you do not own.
