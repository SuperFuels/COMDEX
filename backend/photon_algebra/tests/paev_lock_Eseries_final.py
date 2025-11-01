#!/usr/bin/env python3
"""
Tessaris Photon Algebra - E-Series Lock Protocol
------------------------------------------------
Final archival lock for the E-series (Ensemble Universality & Geometry Invariance).
This script consolidates all verified E-series JSON results, generates SHA-256
hashes, and records a reproducible snapshot into the registry and ledger.
"""

import os, json, hashlib, time

# Base directories
ROOT        = "backend/modules/knowledge"
CONST_DIR   = "backend/photon_algebra/constants"
TEST_DIR    = "backend/photon_algebra/tests"
LOCK_PATH   = os.path.join(CONST_DIR, "Eseries_lock_snapshot.json")
DISC_PATH   = os.path.join(TEST_DIR, "discoveries.json")

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def collect_eseries_jsons():
    """Collect all E-series JSON files in backend/modules/knowledge."""
    files = []
    if not os.path.isdir(ROOT):
        return files
    for f in sorted(os.listdir(ROOT)):
        if f.lower().startswith("e") and f.endswith(".json"):
            files.append(os.path.join(ROOT, f))
    return files

def main():
    print("=== Tessaris E′ Lock Protocol ===")
    os.makedirs(CONST_DIR, exist_ok=True)
    os.makedirs(TEST_DIR, exist_ok=True)

    jsons = collect_eseries_jsons()
    if not jsons:
        print(f"⚠️ No E-series JSON files found in {ROOT}")
        return

    locked = []
    discoveries = []
    for path in jsons:
        try:
            h = sha256_file(path)
            with open(path) as f:
                data = json.load(f)
            locked.append({"file": path, "hash": h})

            # Discovery classification by filename
            name = os.path.basename(path)
            if "E1" in name and "ensemble" in name:
                discoveries.append({"id":"D-E1",
                    "event":"Spontaneous Ensemble Symmetry Breaking",
                    "file": path, "hash": h})
            elif "E4" in name:
                discoveries.append({"id":"D-E4",
                    "event":"Noise-Curvature Resilience Law",
                    "file": path, "hash": h})
            elif "E6h" in name:
                discoveries.append({"id":"D-E6h",
                    "event":"Geometry-Invariant Universality Phase",
                    "file": path, "hash": h})
        except Exception as e:
            print(f"⚠️ Could not process {path}: {e}")

    # Lock snapshot
    entry = {
        "id": f"Eseries_LOCK_{time.strftime('%Y%m%d_%H%M%S')}",
        "event": "E-Series Constants Locked",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "files": locked,
        "discoveries": discoveries,
    }

    with open(LOCK_PATH, "w") as f:
        json.dump(entry, f, indent=2)

    # Update main ledger
    ledger = []
    if os.path.exists(DISC_PATH):
        try:
            with open(DISC_PATH) as f:
                data = json.load(f)
                if isinstance(data, list): ledger = data
                elif isinstance(data, dict): ledger = [data]
        except Exception:
            ledger = []
    ledger.append(entry)

    with open(DISC_PATH, "w") as f:
        json.dump(ledger, f, indent=2)

    # Print summary
    print(f"🔒 Locked constants snapshot -> {LOCK_PATH}")
    print(f"🧾 Discovery ledger updated -> {DISC_PATH}")
    print(f"✅ {len(discoveries)} discoveries classified and archived.\n")

    if discoveries:
        for d in discoveries:
            print(f"  * {d['id']}: {d['event']}")
    else:
        print("i️ No discovery-class results found.")

    print("\n✅ Tessaris E′ constants successfully locked and archived.")

if __name__ == "__main__":
    main()