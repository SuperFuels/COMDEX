#!/usr/bin/env python3
"""
🩺 RMC Integrity Repair Utility — Phase 45H.3
Auto-restores or rebuilds a corrupted Resonant Memory Cache (RMC) file.

Logic:
  • If RMC JSON fails to load → rename it as .corrupt
  • Try to restore from .bak if available
  • If none, create a minimal clean valid cache
"""

import json, os, time
from pathlib import Path

CACHE_PATH = Path("data/memory/resonant_memory_cache.json")
BACKUP_PATH = CACHE_PATH.with_suffix(".bak")
CORRUPT_PATH = CACHE_PATH.with_suffix(".corrupt")

def restore_from_backup():
    if BACKUP_PATH.exists():
        data = json.loads(BACKUP_PATH.read_text(encoding="utf-8"))
        CACHE_PATH.write_text(json.dumps(data, indent=2))
        print(f"[Restore] ✅ Restored from backup → {BACKUP_PATH}")
        return True
    return False

def create_clean_cache():
    clean = {
        "timestamp": time.time(),
        "entries": 0,
        "cache": {},
        "meta": {
            "schema": "ResonantMemoryCache.v2",
            "desc": "Clean rebuild after corruption"
        },
    }
    CACHE_PATH.write_text(json.dumps(clean, indent=2))
    print(f"[Rebuild] 🧩 Created new clean cache → {CACHE_PATH}")

def repair_rmc():
    if not CACHE_PATH.exists():
        print("⚠ No existing RMC found, creating clean file.")
        create_clean_cache()
        return

    try:
        json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        print("✅ Cache already valid — no repair needed.")
        return
    except Exception as e:
        print(f"[Error] Corrupted RMC detected: {e}")
        try:
            os.replace(CACHE_PATH, CORRUPT_PATH)
            print(f"[Backup] Moved bad file → {CORRUPT_PATH}")
        except Exception as e2:
            print(f"[Warning] Could not rename corrupt file: {e2}")

    if restore_from_backup():
        return
    create_clean_cache()

if __name__ == "__main__":
    repair_rmc()