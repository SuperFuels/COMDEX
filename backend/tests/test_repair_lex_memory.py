#!/usr/bin/env python3
"""
🧩 LexMemory Repair Utility
────────────────────────────
Scans and repairs corrupted entries in:
   data/memory/cee_lex_memory.json

• Creates an automatic backup (.lexbak)
• Recovers valid JSON fragments
• Removes syntax errors and incomplete entries
• Reports recovery statistics
"""

import json, re, pathlib

LEX_PATH = pathlib.Path("/workspaces/COMDEX/data/memory/cee_lex_memory.json")
BACKUP_PATH = LEX_PATH.with_suffix(".lexbak")

if not LEX_PATH.exists():
    print(f"❌ No file found at {LEX_PATH}")
    raise SystemExit(1)

# ───────────────────────────────────────────────
# Backup and load
LEX_PATH.replace(BACKUP_PATH)
print(f"[Backup] Created → {BACKUP_PATH}")

text = BACKUP_PATH.read_text(errors="ignore")
text = text.replace("\r", " ").replace("\n", " ")

# Remove any stray characters before first { and after last }
if "{" in text and "}" in text:
    text = text[text.find("{") : text.rfind("}") + 1]

# ───────────────────────────────────────────────
# Try to load as-is first
try:
    data = json.loads(text)
    print(f"✅ Loaded cleanly ({len(data)} entries) — no repair needed.")
    LEX_PATH.write_text(json.dumps(data, indent=2))
    raise SystemExit(0)
except Exception:
    pass

# ───────────────────────────────────────────────
# Attempt fragment recovery
fragments = re.findall(r"\{[^{}]+\}", text)
valid = []
for frag in fragments:
    try:
        obj = json.loads(frag)
        valid.append(obj)
    except Exception:
        continue

# ───────────────────────────────────────────────
# Write repaired version
if valid:
    with open(LEX_PATH, "w", encoding="utf-8") as f:
        json.dump(valid, f, indent=2)
    print(f"✅ Repaired LexMemory — {len(valid)} valid entries recovered.")
else:
    print("❌ No valid fragments could be recovered — check backup manually.")