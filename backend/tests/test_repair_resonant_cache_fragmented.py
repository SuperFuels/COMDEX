#!/usr/bin/env python3
"""
🧩 Fragmented Repair — Resonant Memory Cache
────────────────────────────────────────────
Scans the corrupted cache file and reconstructs as many
valid { ... } JSON fragments as possible into a clean dict.
"""

import json, re
from pathlib import Path

CACHE = Path("/workspaces/COMDEX/data/memory/resonant_memory_cache.json")
BACKUP = CACHE.with_suffix(".fragbak")

if CACHE.exists():
    CACHE.replace(BACKUP)
    print(f"[Backup] Created → {BACKUP}")
else:
    print("❌ No cache file found.")
    exit()

text = BACKUP.read_text(errors="ignore")
# Clean up artifacts
text = text.replace("\n", " ").replace("\r", " ")
text = re.sub(r"[^\{\}\[\]:,0-9A-Za-z_.\"'\\-]", " ", text)

# Find all mini JSON dict fragments
fragments = re.findall(r"\{[^{}]*\}", text)
data = {}
count = 0

for frag in fragments:
    try:
        obj = json.loads(frag)
        if isinstance(obj, dict):
            data.update(obj)
            count += 1
    except Exception:
        continue

with CACHE.open("w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print(f"✅ Rebuilt clean cache with {count} valid fragments → {CACHE}")