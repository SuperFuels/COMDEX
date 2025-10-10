#!/usr/bin/env python3
"""
Tessaris Photon Algebra — G-Series Lock Protocol
------------------------------------------------
Final archival lock for the G-series (Emergent Gravity & Multiscale Stability).
Captures validated constants, summary JSONs, and computed hashes into a reproducible snapshot.
"""

import os, json, hashlib, time

ROOT = "backend/photon_algebra"
CONST_DIR = os.path.join(ROOT, "constants")
TEST_DIR  = os.path.join(ROOT, "tests")
LOCK_PATH = os.path.join(CONST_DIR, "Gseries_lock_snapshot.json")
LEDGER    = os.path.join(TEST_DIR, "discoveries.json")

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("=== Tessaris G′ Lock Protocol ===")
    os.makedirs(CONST_DIR, exist_ok=True)
    os.makedirs(TEST_DIR, exist_ok=True)

    # expected G9/G10 JSON outputs
    candidates = [
        os.path.join(CONST_DIR, "G9_emergent_gravity_coupling.json"),
        os.path.join(CONST_DIR, "G10_regime_cycling_multiscale_stability.json"),
    ]

    locked = []
    for path in candidates:
        if os.path.exists(path):
            h = sha256_file(path)
            locked.append({"file": path, "hash": h})
        else:
            print(f"⚠️ Missing expected G-series file: {path}")

    entry = {
        "id": f"Gseries_LOCK_{time.strftime('%Y%m%d_%H%M%S')}",
        "event": "G-Series Constants Locked",
        "files": locked,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    with open(LOCK_PATH, "w") as f:
        json.dump(entry, f, indent=2)

    # append to discoveries ledger
    ledger = []
    if os.path.exists(LEDGER):
        try:
            with open(LEDGER) as f:
                data = json.load(f)
                if isinstance(data, list): ledger = data
                elif isinstance(data, dict): ledger = [data]
        except Exception:
            ledger = []
    ledger.append(entry)

    with open(LEDGER, "w") as f:
        json.dump(ledger, f, indent=2)

    print(f"🔒 Locked constants snapshot → {LOCK_PATH}")
    print(f"🧾 Discovery ledger updated → {LEDGER}")
    print("\n✅ Tessaris G′ constants successfully locked and archived.")

if __name__ == "__main__":
    main()