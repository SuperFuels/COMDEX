#!/usr/bin/env python3
"""
Initialize a clean, valid ResonantMemoryCache file (with backup).

Usage:
  PYTHONPATH=. python backend/tests/test_init_clean_rmc.py \
      --path /workspaces/COMDEX/data/memory/resonant_memory_cache.json
"""

import argparse, json, sys
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default="data/memory/resonant_memory_cache.json",
                    help="Path to resonant_memory_cache.json")
    args = ap.parse_args()

    rmc = Path(args.path).resolve()
    rmc.parent.mkdir(parents=True, exist_ok=True)

    # Backup if exists
    if rmc.exists():
        backup = rmc.with_suffix(".pre_atomic.bak")
        try:
            rmc.replace(backup)
            print(f"[Backup] Moved existing cache → {backup}")
        except Exception as e:
            print(f"❌ Failed to backup existing cache: {e}")
            sys.exit(1)
    else:
        print("[Init] No existing cache found — will create a fresh one.")

    # Write a minimal valid structure
    valid_cache = {
        "timestamp": 0,
        "entries": 0,
        "cache": {},
        "meta": {"schema": "ResonantMemoryCache.v2", "desc": "Initialized clean cache"}
    }

    try:
        rmc.write_text(json.dumps(valid_cache, indent=2), encoding="utf-8")
        print(f"[Init] Clean valid cache written → {rmc}")
    except Exception as e:
        print(f"❌ Failed to write clean cache: {e}")
        sys.exit(1)

    # Re-read to verify
    try:
        data = json.loads(rmc.read_text(encoding="utf-8"))
        assert isinstance(data, dict) and "cache" in data and isinstance(data["cache"], dict)
        print("[Verify] ✅ JSON structure OK.")
        sys.exit(0)
    except Exception as e:
        print(f"[Verify] ❌ JSON invalid after write: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()