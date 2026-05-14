#!/usr/bin/env python3
# ================================================================
# 🌐 Glyph Registry Updater - Tessaris Lexicon ↔ GlyphOS Sync v3
# ================================================================
"""
Rebuilds/repairs glyph registry across enriched lexicon capsules.

- Reads *.wiki.enriched.phn capsules
- Extracts lemma + a canonical phrase to hash
- Proposes a glyph via the new generator (fallback to compressor if needed)
- Stores via storage API (atomic); leaves bijection/uniqueness to storage
- Injects/updates the *last* GlyphOS registration block in the capsule

Idempotent: re-running is safe.
"""

from __future__ import annotations

import os
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any

# ── Logging ─────────────────────────────────────────────────────
log = logging.getLogger("glyph_registry")
logging.basicConfig(level=logging.INFO, format="%(message)s")

# ── Constants & env ─────────────────────────────────────────────
LEXICON_PATH = Path("data/knowledge/Lexicon_enriched")
CHECKSUM_TAG = "SHA3-256"
MAX_FILES = 120000

# Controls
LIMIT = int(os.getenv("GLYPHOS_LIMIT", "0")) or MAX_FILES
VERIFY = os.getenv("GLYPHOS_VERIFY", "0") == "1"
QUIET = os.getenv("GLYPHOS_QUIET", "0") == "1"
DEBUG = os.getenv("GLYPHOS_DEBUG", "0") == "1"

# ── Imports that can sometimes be touchy; guard gracefully ─────
# Use the storage module as a namespace to avoid NameError/circulars
import backend.modules.glyphos.glyph_storage as glyph_storage

# Prefer the *new* unique generator; fall back to compressor
try:
    from backend.modules.glyphos.glyph_synthesis_engine import generate_unique_symbol as _GEN_IMPL  # type: ignore
except Exception:
    _GEN_IMPL = None

try:
    from backend.modules.glyphos.glyph_synthesis_engine import compress_to_glyphs as _COMPRESS  # type: ignore
except Exception:
    _COMPRESS = None

# Optional symbolic persistence (no-op if unavailable)
try:
    from backend.modules.hexcore.memory_engine import store_memory_entry  # type: ignore
except Exception:
    def store_memory_entry(*a, **k):  # type: ignore
        return None


# ================================================================
# 🔐 Helpers
# ================================================================
import re
from backend.modules.glyphos.constants import RESERVED_GLYPHS, DEFAULT_GLYPH

_GLYPH_RE = re.compile(r'^\s*symbol:\s*(.+)$', flags=re.M)

def _current_symbol_is_reserved(content: str) -> bool:
    """
    True if the capsule has no glyph block, uses the default ✦,
    or contains any reserved/code glyphs (operators/Greek).
    """
    m = _GLYPH_RE.search(content)
    if not m:
        return True  # no glyph block yet -> needs writing
    sym = m.group(1).strip()
    return (sym == DEFAULT_GLYPH) or any(ch in RESERVED_GLYPHS for ch in sym)

def sha3_256_hex(data: bytes) -> str:
    return hashlib.sha3_256(data).hexdigest()


def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
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
        s = line.strip()
        if s.startswith("lemma:"):
            lemma = s.split("lemma:", 1)[1].strip().strip("'\"")
        elif s.startswith("- ") and not definition:
            # first definition bullet only
            definition = s[2:].strip()
    return {"lemma": lemma, "definition": definition or ""}


# ================================================================
# 🧪 Glyph block injection - replace the *last* block
# ================================================================
def inject_or_replace_glyph_block(content: str, glyph_str: str, glyph_checksum: str) -> str:
    header = "# === GlyphOS Registration Block ==="
    lines = content.splitlines()

    # Find the LAST occurrence of the block header.
    start = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip().startswith(header):
            start = i
            break

    new_block = [
        header,
        "glyph:",
        f"  symbol: {glyph_str}",
        f"  checksum: {CHECKSUM_TAG}:{glyph_checksum}",
        "",
    ]

    if start is not None:
        # Replace from the last header onward
        lines = lines[:start] + new_block
    else:
        # Append cleanly with a separating newline if needed
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(new_block)

    return "\n".join(lines) + "\n"


# ================================================================
# 🎯 Glyph proposal (robust wrapper)
# ================================================================
def propose_glyph(lemma: str, definition: str) -> str:
    """
    Prefer the new unique generator; fall back to the compressor path
    if the generator isn't available or its signature differs.
    """
    phrase = f"{lemma}: {definition}"
    # Try new generator
    if _GEN_IMPL:
        try:
            return _GEN_IMPL(phrase, context="lexicon", min_len=1, max_len=3)  # type: ignore
        except TypeError:
            # Signature mismatch -> ignore extras
            try:
                return _GEN_IMPL(phrase)  # type: ignore
            except Exception:
                pass
        except Exception:
            pass

    # Fallback to compressor
    if _COMPRESS:
        out = _COMPRESS(phrase)
        return out[0] if isinstance(out, list) else str(out)

    # Last resort (should never happen): deterministic single char
    # (still stable and unique-ish across runs)
    dig = hashlib.sha3_256(phrase.encode("utf-8")).digest()
    A = "✦✧✩✪✫✬✭✮✯✰✱✲✳✴✵✶✷✸✹✺✻✼✽✾✿❀❁❂❃❄❅❆❇❈❉❊❋"
    return A[dig[0] % len(A)]


# ================================================================
# 🔄 Main updater
# ================================================================
def update_glyph_registry() -> Dict[str, int]:
    log.info("🌐 [GlyphOS] Rebuilding dynamic glyph registry...")
    counters = {"scanned": 0, "updated": 0, "skipped": 0, "conflicts": 0}

    if not LEXICON_PATH.exists():
        log.warning(f"⚠️ Lexicon directory not found: {LEXICON_PATH}")
        return counters

    # Touch registry once so glyph_storage can lazy-load it
    try:
        _ = glyph_storage.get_glyph_registry()
    except Exception as e:
        log.warning(f"⚠️ [GlyphOS] Glyph registry update skipped: {e}")
        return counters

    capsules = list(LEXICON_PATH.rglob("*.wiki.enriched.phn"))[:LIMIT]

    for path in capsules:
        content = safe_read(path)
        if not content.strip():
            counters["skipped"] += 1
            continue

        data = extract_lemma_and_def(content)
        lemma = data.get("lemma")
        if not lemma:
            counters["skipped"] += 1
            continue

        if not _current_symbol_is_reserved(content):
            counters["scanned"] += 1
            counters["skipped"] += 1
            continue

        proposed = propose_glyph(lemma, data.get("definition", ""))
        if DEBUG:
            print(f"[DEBUG] lemma={lemma!r} proposed={proposed!r} file={path.name}")

        # Persist to registry (atomic inside glyph_storage)
        try:
            glyph_storage.store_glyph_entry(lemma, proposed)
        except TypeError:
            # tolerate older signatures like (lemma, glyph, checksum=None, metadata=None)
            glyph_storage.store_glyph_entry(lemma, proposed, None, None)  # type: ignore

        # Rewrite capsule footer block
        glyph_checksum = sha3_256_hex(proposed.encode("utf-8"))
        enriched = inject_or_replace_glyph_block(content, proposed, glyph_checksum)
        safe_write(path, enriched)

        # Optional verification
        if VERIFY:
            after = safe_read(path)
            if f"symbol: {proposed}" not in after:
                log.warning(f"⚠️ Verify failed for {path} (symbol not found after write)")

        # Optional memory note (best-effort)
        try:
            store_memory_entry("glyph_registry", {"lemma": lemma, "glyph": proposed})
        except Exception:
            pass

        counters["updated"] += 1
        counters["scanned"] += 1

        if not QUIET and counters["scanned"] % 5000 == 0:
            log.info(f"... {counters['scanned']} scanned | {counters['updated']} updated")

    log.info(
        f"✅ Glyph Registry Sync - "
        f"{counters['scanned']} scanned | "
        f"{counters['updated']} updated | "
        f"{counters['skipped']} skipped | "
        f"{counters['conflicts']} conflicts"
    )
    return counters


# ================================================================
# 🧪 Standalone exec
# ================================================================
if __name__ == "__main__":
    result = update_glyph_registry()
    print(result)