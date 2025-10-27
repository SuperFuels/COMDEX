#!/usr/bin/env python3
"""
🔧 Test: Repair Resonant Memory Cache JSON
────────────────────────────────────────────
Cleans /workspaces/COMDEX/data/memory/resonant_memory_cache.json
by stripping stray code fragments and verifying valid JSON.
"""

import json
import re
from pathlib import Path

def repair_resonant_cache():
    cache_path = Path("/workspaces/COMDEX/data/memory/resonant_memory_cache.json")
    if not cache_path.exists():
        print("⚠ No cache file found.")
        return

    # Read all text
    text = cache_path.read_text(errors="ignore")

    # Trim to the first { and last }
    if "{" not in text or "}" not in text:
        print("⚠ No valid JSON braces found.")
        return
    text = text[text.find("{"): text.rfind("}") + 1]

    # Remove stray Python code or appended source
    text = re.sub(r">+#!/usr/bin/env.*", "", text, flags=re.S)

    # Validate JSON structure
    try:
        data = json.loads(text)
        print(f"✅ Valid JSON structure detected with {len(data)} top-level keys.")
    except Exception as e:
        print(f"❌ JSON validation failed: {e}")
        return

    # Write back cleaned JSON
    cache_path.write_text(json.dumps(data, indent=2))
    print(f"🧹 Clean JSON restored → {cache_path}")

if __name__ == "__main__":
    repair_resonant_cache()