#!/usr/bin/env python3
"""
H′ — Tessaris Lock Protocol
Consolidates all H′ phase-series constants into a unified snapshot.
"""

import os, json, time, hashlib

CONST_FILE = "backend/photon_algebra/constants/paev_constants.json"
LOCK_FILE  = "backend/photon_algebra/constants/Hprime_lock_snapshot.json"
DISCOVERY_FILE = "backend/photon_algebra/tests/discoveries.json"

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)

def sha256_of_dict(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()

def main():
    print("=== Tessaris H′ Lock Protocol ===")

    consts = load_json(CONST_FILE)
    if not consts:
        print("🚨 No constants found to lock.")
        return

    # Gather all H′ entries
    h_series = {k: v for k, v in consts.items() if k.startswith("Hprime")}
    if not h_series:
        print("🚨 No H′ entries detected in constants file.")
        return

    snapshot = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": CONST_FILE,
        "series": sorted(h_series.keys()),
        "constants": h_series,
    }
    snapshot["hash"] = sha256_of_dict(snapshot)

    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    with open(LOCK_FILE, "w") as f:
        json.dump(snapshot, f, indent=4)

    # Log discovery
    discoveries = load_json(DISCOVERY_FILE)
    if isinstance(discoveries, list):
        discoveries.append({
            "id": f"Hprime_LOCK_{time.strftime('%Y%m%d_%H%M%S')}",
            "event": "H′ Constants Locked",
            "hash": snapshot["hash"],
            "source": CONST_FILE,
            "timestamp": snapshot["timestamp"]
        })
    else:
        discoveries = [discoveries, {
            "id": f"Hprime_LOCK_{time.strftime('%Y%m%d_%H%M%S')}",
            "event": "H′ Constants Locked",
            "hash": snapshot["hash"],
            "source": CONST_FILE,
            "timestamp": snapshot["timestamp"]
        }]
    with open(DISCOVERY_FILE, "w") as f:
        json.dump(discoveries, f, indent=4)

    print(f"🔒 Locked constants snapshot → {LOCK_FILE}")
    print(f"🧾 Discovery ledger updated → {DISCOVERY_FILE}")
    print("\n✅ Tessaris H′ constants successfully locked and archived.")

if __name__ == "__main__":
    main()