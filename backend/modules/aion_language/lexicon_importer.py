"""
Lexicon Importer - Phase 41A
----------------------------
Initial linguistic ingestion layer for Aion.
Loads lexical data (word -> definition -> synonyms/antonyms)
and registers it as LanguageAtoms within the Meaning Field Generator (MFG).

Author: Tessaris Research Group
Date: Phase 41A (October 2025)
"""

import json, logging
from pathlib import Path
from dataclasses import dataclass, asdict
from backend.modules.aion_language.meaning_field_engine import MFG
from backend.modules.aion_language.language_atom_builder import LAB

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Data Model
# ─────────────────────────────────────────────
@dataclass
class LexiconEntry:
    word: str
    definition: str
    synonyms: list
    antonyms: list


# ─────────────────────────────────────────────
# Lexicon Importer Core
# ─────────────────────────────────────────────
class LexiconImporter:
    def __init__(self, lexicon_dir: str = "data/lexicons"):
        self.lexicon_dir = Path(lexicon_dir)
        self.lexicon_dir.mkdir(parents=True, exist_ok=True)
        self.entries: dict[str, LexiconEntry] = {}
        self.count = 0
        logger.info("[LexiconImporter] Initialized")

    # ─────────────────────────────────────────
    def load(self, source: str | Path):
        """Load a JSON lexicon file into memory and register entries."""
        path = Path(source)
        if not path.exists():
            logger.warning(f"[LexiconImporter] Lexicon source not found: {path}")
            return None

        with open(path, "r") as f:
            data = json.load(f)

        for word, meta in data.items():
            entry = self.normalize_entry(
                word,
                meta.get("definition", ""),
                meta.get("synonyms", []),
                meta.get("antonyms", []),
            )
            self.entries[word] = entry
            self.register_to_MFG(entry)

        self.count = len(self.entries)
        logger.info(f"[LexiconImporter] Loaded {self.count} words from {path.name}")
        return self.entries

    # ─────────────────────────────────────────
    def normalize_entry(self, word, definition, synonyms, antonyms) -> LexiconEntry:
        """Basic normalization to clean and structure lexical entries."""
        word = word.strip().lower()
        definition = definition.strip().capitalize()
        synonyms = [s.lower() for s in synonyms]
        antonyms = [a.lower() for a in antonyms]
        return LexiconEntry(word, definition, synonyms, antonyms)

    # ─────────────────────────────────────────
    def register_to_MFG(self, entry: LexiconEntry):
        """
        Registers each lexical entry as a new semantic atom
        inside the Meaning Field Generator and LAB subsystems.
        """
        try:
            atom = LAB.create_atom(entry.word, entry.definition)
            MFG.register(entry.word, {
                "definition": entry.definition,
                "synonyms": entry.synonyms,
                "antonyms": entry.antonyms,
                "atom_ref": atom.get("id", None),
                "semantic_strength": 1.0,
            })
            logger.debug(f"[LexiconImporter] Registered '{entry.word}' -> MFG")
        except Exception as e:
            logger.error(f"[LexiconImporter] Failed to register {entry.word}: {e}")

    # ─────────────────────────────────────────
    def export_to_AKG(self, filename="lexicon_dump.json"):
        """Serialize the imported lexicon to Aion Knowledge Graph format."""
        path = self.lexicon_dir / filename
        data = {w: asdict(e) for w, e in self.entries.items()}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"[LexiconImporter] Exported {len(self.entries)} entries -> {path}")
        return path


# ─────────────────────────────────────────────
# Global Instance
# ─────────────────────────────────────────────
try:
    LEX
except NameError:
    try:
        LEX = LexiconImporter()
        print("📘 LexiconImporter global instance initialized as LEX")
    except Exception as e:
        print(f"⚠️ Could not initialize LexiconImporter: {e}")
        LEX = None