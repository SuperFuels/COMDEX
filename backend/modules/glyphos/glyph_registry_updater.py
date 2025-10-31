#!/usr/bin/env python3
# ================================================================
# 🌐 Glyph Registry Updater — Tessaris Lexicon ↔ GlyphOS Sync v3
# ================================================================
"""
Rebuilds glyph registry across enriched lexicon capsules.

- Reads .wiki.enriched.phn capsules
- Extracts lemma + definition
- Passes through glyph_synthesizer to enforce global uniqueness
- Injects/updates glyph block in file
- Stores into GlyphOS registry + memory

Now aligned with:
  ✅ unified GLYPH_ALPHABET (constants.py)
  ✅ document-format glyph header layer
  ✅ global dedup + deterministic hash
"""

import hashlib, logging
from pathlib import Path
from typing import Dict, Any

# Core — unified compression instead of manual
from backend.modules.glyphos.glyph_synthesis_engine import compress_to_glyphs
from backend.modules.glyphos.glyph_storage import store_glyph_entry, get_glyph_registry
from backend.modules.glyphos.constants import GLYPH_ALPHABET

# Optional symbolic persistence
try:
    from backend.modules.hexcore.memory_engine import store_memory_entry
except Exception:
    store_memory_entry = lambda key, val: None

log = logging.getLogger("glyph_registry")
logging.basicConfig(level=logging.INFO, format="%(message)s")

LEXICON_PATH = Path("data/knowledge/Lexicon_enriched")
CHECKSUM_TAG = "SHA3-256"
MAX_FILES = 120000

# ================================================================
# 🔐 Helpers
# ================================================================
def sha3_256_hex(data: bytes) -> str:
    return hashlib.sha3_256(data).hexdigest()

def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except:
        return ""

def safe_write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

# ================================================================
# 📦 Capsule parsing
# ================================================================
def extract_lemma_and_def(content: str) -> Dict[str, Any]:
    lemma, definition = None, None
    for line in content.splitlines():
        if line.strip().startswith("lemma:"):
            lemma = line.split("lemma:", 1)[1].strip().strip("'\"")
        elif line.strip().startswith("- ") and not definition:
            definition = line.strip("- ").strip()
    return {"lemma": lemma, "definition": definition or ""}

# ================================================================
# 🧪 Glyph block injection
# ================================================================
def inject_or_replace_glyph_block(content: str, glyph_str: str, glyph_checksum: str) -> str:
    lines = content.splitlines()

    new_block = [
        "# === GlyphOS Registration Block ===",
        "glyph:",
        f"  symbol: {glyph_str}",
        f"  checksum: {CHECKSUM_TAG}:{glyph_checksum}",
        "",
    ]

    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("# === GlyphOS Registration Block ==="):
            start = i
            break

    if start is not None:
        lines = lines[:start]

    return "\n".join(lines).rstrip() + "\n" + "\n".join(new_block) + "\n"

# ================================================================
# 🔄 Main updater
# ================================================================
def update_glyph_registry() -> Dict[str, int]:
    log.info("🌐 [GlyphOS] Rebuilding dynamic glyph registry…")
    counters = {"scanned": 0, "updated": 0, "skipped": 0}

    if not LEXICON_PATH.exists():
        log.warning(f"⚠️ Lexicon directory not found: {LEXICON_PATH}")
        return counters

    capsules = list(LEXICON_PATH.rglob("*.wiki.enriched.phn"))[:MAX_FILES]

    for path in capsules:
        content = safe_read(path)
        if not content.strip():
            counters["skipped"] += 1
            continue

        data = extract_lemma_and_def(content)
        lemma = data["lemma"]
        if not lemma:
            counters["skipped"] += 1
            continue

        phrase = f"{lemma}: {data['definition']}"
        glyph_symbol = compress_to_glyphs(phrase)

        # always returns list — enforce consistency
        glyph_str = glyph_symbol[0] if isinstance(glyph_symbol, list) else glyph_symbol
        glyph_checksum = sha3_256_hex(glyph_str.encode("utf-8"))

        enriched = inject_or_replace_glyph_block(content, glyph_str, glyph_checksum)
        safe_write(path, enriched)

        store_glyph_entry(lemma, glyph_str)
        store_memory_entry("glyph_registry", {"lemma": lemma, "glyph": glyph_str})

        counters["updated"] += 1
        counters["scanned"] += 1

        if counters["scanned"] % 5000 == 0:
            log.info(f"… {counters['scanned']} scanned | {counters['updated']} updated")

    log.info(
        f"✅ Glyph Registry Sync complete — "
        f"{counters['scanned']} scanned | "
        f"{counters['updated']} updated | "
        f"{counters['skipped']} skipped"
    )
    return counters

# ================================================================
# 🧪 Standalone exec
# ================================================================
if __name__ == "__main__":
    result = update_glyph_registry()
    print(result)