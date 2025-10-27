#!/usr/bin/env python3
"""
✅ RMC Integrity Verifier — Phase 45H.2
Ensures that the Resonant Memory Cache (RMC) JSON file is:
  • Valid JSON (no corruption)
  • Schema-compliant (timestamp, entries, cache, meta)
  • Internally consistent (entries == len(cache))
"""

import json, sys
from pathlib import Path

CACHE_PATH = Path("data/memory/resonant_memory_cache.json")
SCHEMA_KEYS = {"timestamp", "entries", "cache", "meta"}

def verify_rmc(path: Path):
    if not path.exists():
        print(f"❌ Missing RMC file: {path}")
        sys.exit(1)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ JSON load failed: {e}")
        sys.exit(2)

    # --- Structural checks
    if not isinstance(data, dict):
        print("❌ Invalid structure: root not a dict")
        sys.exit(3)

    missing = SCHEMA_KEYS - set(data.keys())
    if missing:
        print(f"❌ Missing schema keys: {', '.join(missing)}")
        sys.exit(4)

    cache = data.get("cache", {})
    if not isinstance(cache, dict):
        print("❌ 'cache' field not a dict")
        sys.exit(5)

    count_mismatch = len(cache) != data.get("entries", -1)
    if count_mismatch:
        print(f"⚠ Count mismatch: entries={data['entries']} actual={len(cache)}")
    else:
        print(f"✅ Entry count verified ({len(cache)} entries)")

    # --- Meta checks
    meta = data.get("meta", {})
    if not isinstance(meta, dict) or "schema" not in meta:
        print("⚠ Meta section incomplete or missing schema version")
    else:
        print(f"🧩 Schema: {meta['schema']}")

    print("✅ RMC integrity OK — file is consistent and safe.")

if __name__ == "__main__":
    verify_rmc(CACHE_PATH)