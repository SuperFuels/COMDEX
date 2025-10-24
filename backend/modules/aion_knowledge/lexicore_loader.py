"""
🧠 LexiCore Loader — Phase 45F (Language Substrate)
────────────────────────────────────────────────────
Parses lexical data (e.g. Wiktionary JSON dump) into a
normalized structure for the AION Lexical–Semantic Core.

Output:
    data/lexicons/lexicore.lex.json
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Paths
RAW_LEX_PATH = Path("data/raw/wiktionary_dump.json")
OUTPUT_PATH = Path("data/lexicons/lexicore.lex.json")
os.makedirs(OUTPUT_PATH.parent, exist_ok=True)

# Initialize model
MODEL_PATH = "backend/models/all-MiniLM-L6-v2"
model = SentenceTransformer(MODEL_PATH)
logger.info(f"✅ Using MiniLM model from {MODEL_PATH}")

def normalize_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a raw lexical entry into LexiCore schema."""
    lemma = entry.get("word") or entry.get("lemma")
    pos = entry.get("pos", "unknown")
    definition = entry.get("definition", "")
    example = entry.get("example", "")
    phonetic = entry.get("phonetic", "")
    etymology = entry.get("etymology", "")
    
    embedding = model.encode(definition).tolist()

    return {
        "lemma": lemma,
        "pos": pos,
        "definition": definition,
        "example": example,
        "phonetic": phonetic,
        "etymology": etymology,
        "embedding": embedding,
        "meta": {
            "source": "wiktionary",
            "validated": bool(definition),
        },
    }

def load_raw_lexicon() -> List[Dict[str, Any]]:
    """Load raw lexicon file."""
    if not RAW_LEX_PATH.exists():
        raise FileNotFoundError(f"Missing input: {RAW_LEX_PATH}")
    with open(RAW_LEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def build_lexicore():
    """Main pipeline."""
    logger.info("🧩 Building LexiCore...")
    raw_data = load_raw_lexicon()
    normalized = [normalize_entry(e) for e in raw_data if e.get("definition")]
    logger.info(f"✅ Normalized {len(normalized)} lexical entries.")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)
    logger.info(f"💾 Saved LexiCore → {OUTPUT_PATH}")
    return {"entries": len(normalized), "path": str(OUTPUT_PATH)}

if __name__ == "__main__":
    summary = build_lexicore()
    print(json.dumps(summary, indent=2))