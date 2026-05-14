#!/usr/bin/env python3
"""
🧹 Auto-Repair: Resonant Memory Cache
──────────────────────────────────────
Fixes minor JSON corruption such as missing commas or trailing fragments
in /workspaces/COMDEX/data/memory/resonant_memory_cache.json
"""

import json, re
from pathlib import Path

CACHE = Path("/workspaces/COMDEX/data/memory/resonant_memory_cache.json")
BACKUP = CACHE.with_suffix(".autobak")

def auto_repair():
    if not CACHE.exists():
        print("❌ No cache file found.")
        return

    CACHE.replace(BACKUP)
    print(f"[Backup] Created -> {BACKUP}")

    text = BACKUP.read_text(errors="ignore")

    # Keep only JSON content between first { and last }
    text = text[text.find("{"): text.rfind("}") + 1]

    # Replace common corruption patterns
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r",\s*}", "}", text)             # trailing commas
    text = re.sub(r"}\s*{", "}, {", text)          # missing commas between dicts
    text = re.sub(r"([A-Za-z0-9_])\s*:\s*(\w+)", r'"\1": "\2"', text)  # quote bare keys
    text = "{" + text.split("{", 1)[1] if text.count("{") > 1 else text

    try:
        data = json.loads(text)
        CACHE.write_text(json.dumps(data, indent=2))
        print(f"✅ Auto-repaired and saved -> {CACHE}")
        print(f"✅ Valid entries: {len(data)}")
    except Exception as e:
        print(f"❌ Still invalid: {e}")
        print("Please inspect the backup manually:")
        print(f"   -> {BACKUP}")

if __name__ == "__main__":
    auto_repair()