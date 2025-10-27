#!/usr/bin/env python3
"""
🧠 Deep Resonant Cache Repair
─────────────────────────────
Performs full object-level validation of
data/memory/resonant_memory_cache.json.

- Backs up existing file (.deepbak)
- Iterates through all key/value pairs
- Removes malformed resonance entries
- Ensures all fields (ρ, I, SQI, count) are valid numbers
"""

import json, pathlib, time

CACHE_PATH = pathlib.Path("/workspaces/COMDEX/data/memory/resonant_memory_cache.json")
BACKUP_PATH = CACHE_PATH.with_suffix(".deepbak")

if not CACHE_PATH.exists():
    print("❌ Cache file missing.")
    raise SystemExit(1)

# Backup
CACHE_PATH.replace(BACKUP_PATH)
print(f"[Backup] Created → {BACKUP_PATH}")

# Try to parse
try:
    data = json.loads(BACKUP_PATH.read_text(errors="ignore"))
except Exception as e:
    print(f"[Error] Could not parse backup: {e}")
    raise SystemExit(1)

if not isinstance(data, dict):
    print("❌ Cache root is not a dict.")
    raise SystemExit(1)

clean = {}
invalid = 0

for key, val in data.items():
    if not isinstance(val, dict):
        invalid += 1
        continue
    try:
        rho = float(val.get("ρ", val.get("rho", 0)))
        I = float(val.get("I", 0))
        sqi = float(val.get("SQI", 0))
        count = int(val.get("count", 1))
        if any(map(lambda x: x != x, [rho, I, sqi])):  # NaN check
            raise ValueError("NaN values")
        clean[key] = {"ρ": rho, "I": I, "SQI": sqi, "count": count}
    except Exception:
        invalid += 1
        continue

CACHE_PATH.write_text(json.dumps(clean, indent=2))
print(f"✅ Cleaned {len(clean)} entries (removed {invalid}).")
print(f"🕒 Completed at {time.strftime('%H:%M:%S')}")