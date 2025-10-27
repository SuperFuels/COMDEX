#!/usr/bin/env python3
"""
📘 Export LexMemory Snapshot
────────────────────────────
Rebuilds `cee_lex_memory.json` from enriched lexical capsules.
"""

import json, re, logging
from pathlib import Path

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

SRC_DIRS = [
    Path("/tmp/Lexicon_enriched"),
    Path("data/knowledge/Lexicon_enriched")
]

OUT_PATH = Path("/workspaces/COMDEX/data/memory/cee_lex_memory.json")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

def extract_lemma_and_definition(text: str):
    """Pull lemma and short definition from enriched capsule."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    lemma = None
    for l in lines:
        if l.startswith("lemma:") or l.startswith("word:"):
            lemma = re.sub(r"^(lemma|word):", "", l).strip()
            break
    defs = [l for l in lines if "definition" in l.lower() or "means" in l.lower()]
    return lemma, defs[0] if defs else None

def export_snapshot():
    for src_dir in SRC_DIRS:
        if src_dir.exists():
            log.info(f"[Export] Scanning {src_dir}")
            data = {}
            for path in src_dir.rglob("*.enriched.phn"):
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                    lemma, definition = extract_lemma_and_definition(text)
                    if lemma and definition:
                        data[lemma] = {"definition": definition, "path": str(path)}
                except Exception as e:
                    log.warning(f"[Export] Failed {path.name}: {e}")
            OUT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            log.info(f"[Export] ✅ Wrote {len(data)} entries → {OUT_PATH}")
            return
    log.error("[Export] ❌ No valid source directory found.")

if __name__ == "__main__":
    export_snapshot()