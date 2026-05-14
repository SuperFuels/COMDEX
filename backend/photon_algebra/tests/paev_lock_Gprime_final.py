#!/usr/bin/env python3
"""
Tessaris - G′ Lock Protocol
Locks the finalized G′ constants and concordance data for archival integrity.
This script freezes the current constants, computes a registry hash,
and updates the discovery ledger with a timestamped entry.
"""

import os, json, hashlib, time
from pathlib import Path

CONSTANTS_PATH = Path("backend/photon_algebra/constants/paev_constants.json")
DISCOVERY_PATH = Path("backend/photon_algebra/tests/discoveries.json")
LOCK_PATH = Path("backend/photon_algebra/constants/Gprime_lock_snapshot.json")

def hash_file(path):
    """Return SHA256 of file contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()

def lock_constants():
    """Freeze current constants and record a lock snapshot."""
    if not CONSTANTS_PATH.exists():
        print(f"⚠️ Constants file not found: {CONSTANTS_PATH}")
        return False

    with open(CONSTANTS_PATH) as f:
        constants = json.load(f)

    snapshot = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": str(CONSTANTS_PATH),
        "constants": constants,
        "hash": hash_file(CONSTANTS_PATH)
    }

    # Save lock snapshot
    os.makedirs(LOCK_PATH.parent, exist_ok=True)
    with open(LOCK_PATH, "w") as f:
        json.dump(snapshot, f, indent=4)
    print(f"🔒 Locked constants snapshot -> {LOCK_PATH}")

    # Update discovery ledger
    os.makedirs(DISCOVERY_PATH.parent, exist_ok=True)
    if DISCOVERY_PATH.exists():
        with open(DISCOVERY_PATH) as f:
            try:
                ledger = json.load(f)
            except json.JSONDecodeError:
                ledger = []
    else:
        ledger = []

    ledger.append({
        "id": f"G′_LOCK_{time.strftime('%Y%m%d_%H%M%S')}",
        "event": "G′ Constants Locked",
        "hash": snapshot["hash"],
        "source": str(CONSTANTS_PATH),
        "timestamp": snapshot["timestamp"]
    })

    with open(DISCOVERY_PATH, "w") as f:
        json.dump(ledger, f, indent=4)
    print(f"🧾 Discovery ledger updated -> {DISCOVERY_PATH}")

    print("\n✅ Tessaris G′ constants successfully locked and archived.")
    return True


if __name__ == "__main__":
    print("=== Tessaris G′ Lock Protocol ===")
    success = lock_constants()
    if not success:
        exit(1)