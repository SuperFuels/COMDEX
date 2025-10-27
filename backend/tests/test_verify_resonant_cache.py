#!/usr/bin/env python3
"""
✅ Verify Resonant Memory Cache Integrity (recursive deep scan)
──────────────────────────────────────────────────────────────
Detects nested 'cache' layers, validates resonance entries,
and reports an overall integrity percentage.
"""

import json
from pathlib import Path
from math import isnan

CACHE = Path("/workspaces/COMDEX/data/memory/resonant_memory_cache.json")

def is_bad(val):
    return val is None or (isinstance(val, float) and isnan(val))

def count_entries(node):
    """Recursively count valid resonance dicts."""
    total = valid = 0
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, dict):
                if any(x in v for x in ("φ", "μ", "λ", "q_val", "phase", "coherence")):
                    total += 1
                    if not any(is_bad(v.get(x)) for x in ("φ", "μ", "q_val", "phase", "coherence") if x in v):
                        valid += 1
                else:
                    t, vld = count_entries(v)
                    total += t
                    valid += vld
    return total, valid

def verify_cache():
    if not CACHE.exists():
        print("❌ No cache file found.")
        return

    try:
        data = json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ JSON validation failed: {e}")
        return

    total, valid = count_entries(data)
    pct = (valid / max(total, 1)) * 100
    print(f"🔍 Verified {valid}/{total} resonance entries — {pct:.2f}% valid")

    if pct >= 99.9:
        print("✅ Cache integrity GOOD — safe for reinforcement and training.")
    elif pct >= 95:
        print("⚠ Partial corruption — training possible, but clean soon.")
    else:
        print("❌ Significant corruption — inspect backup files immediately.")


if __name__ == "__main__":
    verify_cache()