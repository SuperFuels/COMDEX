#!/usr/bin/env python3
"""
🧩 Resonant Memory Cache — Normalize + Reindex Utility
──────────────────────────────────────────────────────
Cleans malformed JSON, merges duplicate resonance keys,
and rewrites a stable `resonant_memory_cache.json`.

Outputs:
  • data/memory/resonant_memory_cache.cleanbak
  • data/memory/resonant_memory_cache.json (cleaned)
"""

import json, re, pathlib, time
from collections import defaultdict

CACHE_PATH = pathlib.Path("/workspaces/COMDEX/data/memory/resonant_memory_cache.json")
BACKUP_PATH = CACHE_PATH.with_suffix(".cleanbak")

# ───────────────────────────────────────────────
if not CACHE_PATH.exists():
    print(f"❌ No cache file found at {CACHE_PATH}")
    raise SystemExit(1)

CACHE_PATH.replace(BACKUP_PATH)
print(f"[Backup] Created → {BACKUP_PATH}")

text = BACKUP_PATH.read_text(errors="ignore")
text = text.replace("\r", " ").replace("\n", " ")

# Trim to valid JSON boundaries
if "{" in text and "}" in text:
    text = text[text.find("{"): text.rfind("}") + 1]

# Try fast load
try:
    cache = json.loads(text)
    print(f"✅ Cache loaded directly ({len(cache)} entries) — no normalization needed.")
    CACHE_PATH.write_text(json.dumps(cache, indent=2))
    raise SystemExit(0)
except Exception:
    pass

# ───────────────────────────────────────────────
# Recover individual fragments
fragments = re.findall(r'\"[^"]+\"\s*:\s*\{[^{}]*\}', text)
merged = defaultdict(list)
valid = 0

for frag in fragments:
    frag = "{" + frag + "}"
    try:
        obj = json.loads("{" + frag.split(":", 1)[1] + "}")
        key = frag.split(":", 1)[0].strip('" {')
        merged[key].append(obj)
        valid += 1
    except Exception:
        continue

# Merge duplicates by averaging numeric fields
final_cache = {}
for key, entries in merged.items():
    combined = {}
    nums = {}
    for e in entries:
        for k, v in e.items():
            if isinstance(v, (int, float)):
                nums.setdefault(k, []).append(v)
            else:
                combined[k] = v
    for k, vals in nums.items():
        combined[k] = round(sum(vals) / len(vals), 4)
    final_cache[key] = combined

# ───────────────────────────────────────────────
CACHE_PATH.write_text(json.dumps(final_cache, indent=2))
print(f"✅ Normalized {len(final_cache)} resonance entries → {CACHE_PATH}")
print(f"🕒 Completed at {time.strftime('%H:%M:%S')}")