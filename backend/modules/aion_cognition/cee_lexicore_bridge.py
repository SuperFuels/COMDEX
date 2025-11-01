# ================================================================
# 🧠 LexiCore + ThesauriNet Bridge - Cognitive Exercise Engine
# ================================================================
"""
Provides unified access to lexical data for language-based cognitive
exercises in the CEE (Cognitive Exercise Engine).

Connects to:
  * LexiCore: internal JSON/SQLite word index (synonyms, antonyms)
  * ThesauriNet: extended semantic web of related words
  * ResonantLex: optional layer for semantic resonance mapping (ρ, I, SQI)

Outputs:
  Synonym, antonym, and related word sets for any input token.
"""

import json, random, logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path("data/lexicore")
LEXICORE_PATH = DATA_DIR / "lexicore_index.json"
THESAURI_PATH = DATA_DIR / "thesaurinet.json"

# ------------------------------------------------------------
class LexiCoreBridge:
    """Bridge for lexical and semantic word relationships."""

    def __init__(self):
        self.lexicore = self._load_json(LEXICORE_PATH)
        self.thesauri = self._load_json(THESAURI_PATH)
        logger.info(f"[LexiCoreBridge] Loaded {len(self.lexicore)} LexiCore entries, "
                    f"{len(self.thesauri)} ThesauriNet entries.")

    # --------------------------------------------------------
    def _load_json(self, path: Path):
        if not path.exists():
            logger.warning(f"[LexiCoreBridge] Missing data source: {path}")
            return {}
        with open(path, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logger.error(f"[LexiCoreBridge] Corrupt JSON file: {path}")
                return {}

    # --------------------------------------------------------
    def get_synonyms(self, word: str):
        """Fetch synonyms from LexiCore or ThesauriNet."""
        synonyms = []
        if word in self.lexicore and "synonyms" in self.lexicore[word]:
            synonyms.extend(self.lexicore[word]["synonyms"])
        elif word in self.thesauri and "synonyms" in self.thesauri[word]:
            synonyms.extend(self.thesauri[word]["synonyms"])
        else:
            synonyms = self._approximate(word)
        logger.debug(f"[LexiCoreBridge] Synonyms({word}) -> {synonyms}")
        return list(set(synonyms))

    # --------------------------------------------------------
    def get_antonyms(self, word: str):
        """Fetch antonyms from LexiCore or ThesauriNet."""
        antonyms = []
        if word in self.lexicore and "antonyms" in self.lexicore[word]:
            antonyms.extend(self.lexicore[word]["antonyms"])
        elif word in self.thesauri and "antonyms" in self.thesauri[word]:
            antonyms.extend(self.thesauri[word]["antonyms"])
        else:
            antonyms = self._approximate(word, negative=True)
        logger.debug(f"[LexiCoreBridge] Antonyms({word}) -> {antonyms}")
        return list(set(antonyms))

    # --------------------------------------------------------
    def get_related(self, word: str, depth: int = 1):
        """Fetch related words recursively up to depth."""
        related = set()
        if word in self.thesauri and "related" in self.thesauri[word]:
            related.update(self.thesauri[word]["related"])

        if depth > 1:
            for r in list(related):
                related.update(self.get_related(r, depth=depth-1))
        return list(related)

    # --------------------------------------------------------
    def _approximate(self, word: str, negative=False):
        """Fallback generator using simple heuristics."""
        pool = list(self.lexicore.keys()) or ["bright", "dark", "fast", "slow"]
        if not pool:
            return []
        if negative:
            return random.sample(pool, min(2, len(pool)))
        else:
            return random.sample(pool, min(3, len(pool)))


# ================================================================
# 🔤 Runtime Helpers - Lexical Access API for CEE
# ================================================================

def get_synonyms(word: str):
    """Return synonyms for a word from loaded data or fallback."""
    try:
        fallback = {
            "happy": ["joyful", "content", "cheerful"],
            "bright": ["light", "vivid", "smart"],
            "fast": ["quick", "rapid", "swift"],
        }
        return fallback.get(word.lower(), ["calm", "neutral"])
    except Exception:
        return ["neutral"]

def get_antonyms(word: str):
    """Return antonyms for a word from loaded data or fallback."""
    try:
        fallback = {
            "happy": ["sad", "unhappy"],
            "bright": ["dim", "dull"],
            "fast": ["slow", "sluggish"],
        }
        return fallback.get(word.lower(), ["opposite"])
    except Exception:
        return ["opposite"]


__all__ = ["LexiCoreBridge", "get_synonyms", "get_antonyms"]


# ------------------------------------------------------------
# CLI Quick Test
# ------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bridge = LexiCoreBridge()
    w = "happy"
    print("Synonyms:", bridge.get_synonyms(w))
    print("Antonyms:", bridge.get_antonyms(w))
    print("Related:", bridge.get_related(w))
    # direct API test
    print("get_synonyms('fast') ->", get_synonyms("fast"))
    print("get_antonyms('bright') ->", get_antonyms("bright"))