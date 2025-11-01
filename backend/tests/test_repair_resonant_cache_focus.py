#!/usr/bin/env python3
"""
🧩 Focused Repair - ResonantMemoryCache
Shows the first 300 chars around the JSON error and attempts targeted fix.
"""

import json, re
from pathlib import Path

CACHE = Path("/workspaces/COMDEX/data/memory/resonant_memory_cache.autobak")
TARGET = Path("/workspaces/COMDEX/data/memory/resonant_memory_cache.json")

print(f"[Scan] Reading {CACHE}")
text = CACHE.read_text(errors="ignore")

# find region around column 79
snippet = text[:300]
print("\n[Preview near start]")
print("-" * 80)
print(snippet)
print("-" * 80)

# Attempt targeted fixes
text = re.sub(r"\}\s*\{", "}, {", text)     # missing comma between dicts
text = re.sub(r",\s*\}", "}", text)         # stray commas
text = re.sub(r"\{,\s*", "{", text)         # comma after opening brace
text = text[text.find("{"): text.rfind("}") + 1]

try:
    data = json.loads(text)
    TARGET.write_text(json.dumps(data, indent=2))
    print(f"✅ Fixed & saved -> {TARGET} ({len(data)} entries)")
except json.JSONDecodeError as e:
    loc = e.pos
    print(f"❌ Still invalid near char {loc}: {e}")
    print(f"Context -> {text[max(0, loc-100):loc+100]}")