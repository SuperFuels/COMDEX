#!/usr/bin/env python3
"""
🩺 Hardcut Repair for resonant_memory_cache.json
───────────────────────────────────────────────
Finds the last complete JSON object and trims any trailing
garbage (like duplicated scripts or unfinished braces).
"""

import json, re
from pathlib import Path

CACHE = Path("/workspaces/COMDEX/data/memory/resonant_memory_cache.json")
BACKUP = CACHE.with_suffix(".hardbak")

# 1. Backup first
CACHE.replace(BACKUP)
print(f"[Backup] Created -> {BACKUP}")

# 2. Read all
txt = BACKUP.read_text(errors="ignore")

# 3. Trim before first { and after last }
txt = txt[txt.find("{"): txt.rfind("}") + 1]

# 4. Remove embedded Python/script artifacts
txt = re.sub(r"#+!\/usr.*", "", txt, flags=re.S)
txt = re.sub(r">>>+.*", "", txt, flags=re.S)
txt = re.sub(r"<<<?.*", "", txt, flags=re.S)

# 5. Validate progressively from the end
cut = len(txt)
while cut > 0:
    try:
        json.loads(txt[:cut])
        CACHE.write_text(txt[:cut])
        print(f"✅ Recovered clean JSON -> {CACHE}")
        break
    except Exception as e:
        cut = txt.rfind("}", 0, cut - 1)
        if cut <= 0:
            print(f"❌ Could not recover: {e}")
            break
else:
    print("❌ No valid segment found.")