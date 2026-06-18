"""
Parser for airodump-ng CSV output files.

Airodump writes CSV with two sections separated by a blank line:
  Section 1: Access Points
  Section 2: Associated Clients
"""

import csv
import os
from io import StringIO


def parse_airodump_csv(filepath):
    """
    Parse an airodump-ng CSV file.

    Returns:
        (aps, clients) - two lists of dicts
        aps keys: bssid, first_seen, last_seen, channel, speed, privacy,
                  cipher, auth, power, beacons, ivs, lan_ip, essid
        clients keys: station, first_seen, last_seen, power, packets,
                      bssid, probed_essids
    """
    if not os.path.exists(filepath):
        return [], []

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()
    except (IOError, OSError):
        return [], []

    # Split into AP section and client section on the blank line
    # Airodump separates them with a line that's empty or just whitespace
    sections = raw.split("\n\n")
    if not sections:
        return [], []

    aps = _parse_ap_section(sections[0])
    clients = _parse_client_section(sections[1]) if len(sections) > 1 else []

    return aps, clients


def _parse_ap_section(text):
    """Parse the access point section of the CSV."""
    aps = []
    lines = text.strip().splitlines()
    if not lines:
        return aps

    # First line is header, skip it
    # Header: BSSID, First time seen, Last time seen, channel, Speed, Privacy, Cipher, Authentication, Power, # beacons, # IV, LAN IP, ID-length, ESSID, Key
    for line in lines[1:]:
        line = line.strip()
        if not line or line.startswith("BSSID"):
            continue

        # CSV parse the line (handles commas in ESSID)
        reader = csv.reader(StringIO(line))
        try:
            fields = next(reader)
        except StopIteration:
            continue

        if len(fields) < 14:
            continue

        # Strip whitespace from all fields
        fields = [f.strip() for f in fields]

        ap = {
            "bssid": fields[0],
            "first_seen": fields[1],
            "last_seen": fields[2],
            "channel": fields[3],
            "speed": fields[4],
            "privacy": fields[5],
            "cipher": fields[6],
            "auth": fields[7],
            "power": _safe_int(fields[8]),
            "beacons": _safe_int(fields[9]),
            "ivs": _safe_int(fields[10]),
            "lan_ip": fields[11],
            "essid": fields[13] if len(fields) > 13 else "",
        }
        aps.append(ap)

    return aps


def _parse_client_section(text):
    """Parse the client/station section of the CSV."""
    clients = []
    lines = text.strip().splitlines()
    if not lines:
        return clients

    # Header: Station MAC, First time seen, Last time seen, Power, # packets, BSSID, Probed ESSIDs
    for line in lines[1:]:
        line = line.strip()
        if not line or line.startswith("Station"):
            continue

        reader = csv.reader(StringIO(line))
        try:
            fields = next(reader)
        except StopIteration:
            continue

        if len(fields) < 6:
            continue

        fields = [f.strip() for f in fields]

        client = {
            "station": fields[0],
            "first_seen": fields[1],
            "last_seen": fields[2],
            "power": _safe_int(fields[3]),
            "packets": _safe_int(fields[4]),
            "bssid": fields[5],
            "probed_essids": fields[6] if len(fields) > 6 else "",
        }
        clients.append(client)

    return clients


def find_latest_csv(directory, prefix):
    """
    Find the most recent airodump CSV in a directory.
    Airodump appends -01, -02, etc. to filenames.
    """
    candidates = []
    for f in os.listdir(directory):
        if f.startswith(prefix) and f.endswith(".csv"):
            candidates.append(os.path.join(directory, f))

    if not candidates:
        return None

    # Most recently modified
    return max(candidates, key=os.path.getmtime)


def _safe_int(val):
    """Convert to int, return -1 on failure (airodump uses -1 for no signal)."""
    try:
        return int(val)
    except (ValueError, TypeError):
        return -1
