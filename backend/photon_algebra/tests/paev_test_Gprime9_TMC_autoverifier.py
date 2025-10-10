#!/usr/bin/env python3
"""
Test G′9 — Tessaris AutoVerifier
Automated TMC monitoring system for continuous model coherence verification.
Supports both continuous watch mode and single-shot (--once) verification.

Implements the full Tessaris Standard Test Protocol:
- Reads latest constant deviations from prior G′ tests
- Computes Tessaris Model Concordance (TMC) index
- Logs results to CSV and JSON registries
- Updates discovery ledger (discovery.json)
- Auto-synthesizes missing CSVs from console logs
- Color-coded terminal feedback for drift and coherence
"""

import os
import sys
import time
import csv
import argparse
import numpy as np
import json
from pathlib import Path
import re

# --- File references ---
WATCHED_RESULTS = [
    "results_Gprime6_global_concordance.csv",
    "results_Gprime7_grav_normalization.csv",
    "results_Gprime8_TMC_final.csv",
]

OUTPUT_FILE = "results_Gprime9_TMC_autoverifier_log.csv"
DISCOVERY_FILE = "backend/photon_algebra/tests/discoveries.json"
CONSTANTS_FILE = "backend/photon_algebra/constants/paev_constants.json"
CHECK_INTERVAL = 15  # seconds between scans


# ------------------------- Utility Functions -------------------------

def color(text, code):
    """Apply ANSI terminal colors."""
    return f"\033[{code}m{text}\033[0m"


def synthesize_missing_csvs():
    """
    Try to reconstruct missing CSVs from previous console output or logs.
    """
    print(color("🧩 Attempting to auto-synthesize missing CSVs from console output...", 33))
    candidates = sorted(Path(".").glob("*.log")) + [Path("stdout.txt"), Path("console.txt")]

    for f in WATCHED_RESULTS:
        if os.path.exists(f):
            continue
        for cand in candidates:
            if not cand.exists():
                continue
            text = cand.read_text(errors="ignore")
            match = re.search(
                r"Constant,Effective,Reference,Deviation_%(.+?)TMC_Index,([0-9eE\.\-]+)",
                text,
                re.S
            )
            if match:
                block = (
                    "Constant,Effective,Reference,Deviation_%\n"
                    + match.group(1).strip()
                    + f"\nTMC_Index,{match.group(2)}\n"
                )
                Path(f).write_text(block)
                print(color(f"✅ Reconstructed {f} from {cand.name}", 32))
                break


def read_latest_constants():
    """Pull constants and deviations from available result CSVs."""
    data = {}
    for f in WATCHED_RESULTS:
        if not os.path.exists(f):
            continue
        with open(f) as csvfile:
            reader = csv.reader(csvfile)
            for r in reader:
                if not r or r[0].startswith("#"):
                    continue
                if len(r) >= 4 and r[0] in ("alpha", "hbar", "m_e", "G"):
                    try:
                        data[r[0]] = float(r[3])
                    except ValueError:
                        continue
                elif r[0].strip() == "TMC_Index":
                    try:
                        data["TMC_Index"] = float(r[1])
                    except ValueError:
                        continue
    return data


def compute_TMC(devs):
    """Compute the Tessaris Model Concordance Index (RMS of deviations)."""
    vals = [devs[k] for k in ("alpha", "hbar", "m_e", "G") if k in devs]
    return float(np.sqrt(np.mean(np.array(vals) ** 2))) if vals else None


def log_update(devs, TMC):
    """Append verification result to CSV log."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    with open(OUTPUT_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if f.tell() == 0:
            writer.writerow(["Timestamp", "alpha_%", "hbar_%", "m_e_%", "G_%", "TMC_Index_%"])
        writer.writerow([
            timestamp,
            devs.get("alpha", ""), devs.get("hbar", ""),
            devs.get("m_e", ""), devs.get("G", ""),
            round(TMC, 6),
        ])

    print(f"[{color(timestamp, 36)}] AutoVerifier → TMC = {color(f'{TMC:.3f} %', 35)}")

    if TMC < 1.0:
        print(color("✅ Concordance maintained — system coherent.", 32))
    elif TMC < 5.0:
        print(color("⚠️ Minor drift — check recent curvature deltas.", 33))
    else:
        print(color("🚨 Concordance failure — re-run gravitational normalization!", 31))


def update_constants_registry(devs, TMC):
    """Write verified deviations to the shared constants JSON."""
    os.makedirs(os.path.dirname(CONSTANTS_FILE), exist_ok=True)
    existing = {}
    if os.path.exists(CONSTANTS_FILE):
        try:
            existing = json.load(open(CONSTANTS_FILE))
        except Exception:
            existing = {}

    existing["Gprime9"] = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "alpha_%": devs.get("alpha"),
        "hbar_%": devs.get("hbar"),
        "m_e_%": devs.get("m_e"),
        "G_%": devs.get("G"),
        "TMC_Index_%": TMC,
    }

    with open(CONSTANTS_FILE, "w") as f:
        json.dump(existing, f, indent=2)
    print(color(f"📘 Updated constants registry → {CONSTANTS_FILE}", 36))


def update_discovery_ledger(devs, TMC):
    """Append discovery record to discovery ledger (discoveries.json)."""
    os.makedirs(os.path.dirname(DISCOVERY_FILE), exist_ok=True)
    ledger = []
    if os.path.exists(DISCOVERY_FILE):
        try:
            ledger = json.load(open(DISCOVERY_FILE))
        except Exception:
            ledger = []

    entry = {
        "test": "G′9 — Tessaris AutoVerifier",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": "verification",
        "status": (
            "coherent" if TMC < 1.0 else
            "drift" if TMC < 5.0 else
            "failure"
        ),
        "TMC_Index": round(TMC, 6),
        "constants": {k: devs.get(k) for k in ("alpha", "hbar", "m_e", "G")},
    }

    ledger.append(entry)
    with open(DISCOVERY_FILE, "w") as f:
        json.dump(ledger, f, indent=2)
    print(color(f"🧾 Discovery ledger updated → {DISCOVERY_FILE}", 36))


# ------------------------- Main Entry -------------------------

def main():
    parser = argparse.ArgumentParser(description="Tessaris AutoVerifier (TMC monitor)")
    parser.add_argument("--once", action="store_true", help="Run one verification and exit")
    args = parser.parse_args()

    print(color("=== G′9 — Tessaris AutoVerifier (Realtime TMC Monitor) ===", 36))
    print(f"Monitoring: {', '.join(WATCHED_RESULTS)}\n")

    # Read constants
    devs = read_latest_constants()
    if not devs:
        synthesize_missing_csvs()
        devs = read_latest_constants()
        if not devs:
            print(color("⚠️ No constants found — ensure prior G′ results exist.", 33))
            sys.exit(1)

    TMC = compute_TMC(devs)
    if TMC is None:
        print(color("⚠️ Could not compute TMC — missing deviations.", 33))
        sys.exit(1)

    # Logging and registry updates
    log_update(devs, TMC)
    update_constants_registry(devs, TMC)
    update_discovery_ledger(devs, TMC)

    if args.once:
        print(color("\n✅ Single verification complete. Exiting.", 32))
        sys.exit(0)

    # Continuous monitoring mode
    seen = {}
    while True:
        time.sleep(CHECK_INTERVAL)
        devs = read_latest_constants()
        if not devs:
            continue
        TMC = compute_TMC(devs)
        key = tuple(round(devs.get(k, 0), 6) for k in ("alpha", "hbar", "m_e", "G"))
        if key != seen.get("last_key"):
            log_update(devs, TMC)
            update_constants_registry(devs, TMC)
            update_discovery_ledger(devs, TMC)
            seen["last_key"] = key


if __name__ == "__main__":
    main()