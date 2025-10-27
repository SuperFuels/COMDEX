#!/usr/bin/env python3
"""
✂️ Final Trim & Validation — Resonant Memory Cache
──────────────────────────────────────────────────
Removes trailing garbage beyond the last valid JSON segment
and re-verifies the structure.
"""

import json
from pathlib import Path

CACHE = Path("/workspaces/COMDEX/data/memory/resonant_memory_cache.json")
BACKUP = CACHE.with_suffix(".trimmedbak")

CACHE.replace(BACKUP)
print(f"[Backup] Created → {BACKUP}")

text = BACKUP.read_text(errors="ignore")

# Cut to last full closing brace
clean = text[: text.rfind("}") + 1]

try:
    data = json.loads(clean)
    CACHE.write_text(json.dumps(data, indent=2))
    print(f"✅ Clean JSON restored ({len(data)} entries) → {CACHE}")
except Exception as e:
    print(f"❌ Still invalid: {e}")
    # Try stepwise trimming from the end until it loads
    for i in range(1, 500):
        cut = clean.rfind("}", 0, len(clean) - i)
        if cut <= 0:
            print("❌ No valid segment found.")
            break
        try:
            data = json.loads(clean[:cut + 1])
            CACHE.write_text(json.dumps(data, indent=2))
            print(f"✅ Trimmed and recovered ({len(data)} entries) → {CACHE}")
            break
        except Exception:
            continue