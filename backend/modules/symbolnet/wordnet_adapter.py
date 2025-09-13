# File: backend/modules/symbolnet/wordnet_adapter.py
from __future__ import annotations

import logging
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Lazy NLTK/WordNet handles
_HAVE_NLTK: bool = False
_wn = None  # set to nltk.corpus.wordnet if available and loaded


def _init_wordnet() -> bool:
    """
    Lazily initialize NLTK WordNet.
    - Never raises: returns False if unavailable.
    - If SYMBOLNET_AUTO_DOWNLOAD_NLTK=1|true, attempts a quiet corpus download.
    """
    global _HAVE_NLTK, _wn
    if _HAVE_NLTK and _wn is not None:
        return True

    try:
        import nltk  # type: ignore
        from nltk.corpus import wordnet as wn  # type: ignore

        try:
            wn.ensure_loaded()
        except Exception:
            auto = os.environ.get("SYMBOLNET_AUTO_DOWNLOAD_NLTK", "0").lower() in {"1", "true", "yes"}
            if auto:
                try:
                    nltk.download("wordnet", quiet=True)
                    nltk.download("omw-1.4", quiet=True)
                    wn.ensure_loaded()
                except Exception as e:  # still not usable
                    logger.warning("NLTK present but WordNet corpora unavailable: %s", e)
                    _HAVE_NLTK = False
                    _wn = None
                    return False
            else:
                logger.warning(
                    "NLTK present but WordNet corpora not loaded. "
                    "Set SYMBOLNET_AUTO_DOWNLOAD_NLTK=1 to auto-download at runtime."
                )
                _HAVE_NLTK = False
                _wn = None
                return False

        _wn = wn
        _HAVE_NLTK = True
        return True

    except Exception:  # NLTK not installed
        logger.warning(
            "NLTK not installed. WordNet features disabled. "
            "Install with `pip install nltk` and download corpora "
            "(wordnet, omw-1.4) to enable."
        )
        _HAVE_NLTK = False
        _wn = None
        return False


def query_wordnet(term: str, context: Optional[str] = None, mode: str = "default") -> List[Dict[str, Any]]:
    """
    Query WordNet for synonyms, definitions, and hypernyms of a given term.
    Returns a list of dicts compatible with SymbolNet format:

      {
        "label": str,            # human-friendly lemma (underscores → spaces)
        "source": "wordnet",
        "type": "synonym"|"hypernym",
        "description": str,      # synset definition
        "score": float           # heuristic score (kept to match original)
      }

    Never raises if NLTK/WordNet are missing; returns [] and logs a warning.
    Parameters `context` and `mode` are accepted for API parity (not required here).
    """
    results: List[Dict[str, Any]] = []

    if not term:
        return results

    if not _init_wordnet() or _wn is None:
        # Graceful no-op when NLTK/WordNet unavailable
        return results

    try:
        logger.info(f"📚 Querying WordNet for term: {term}")
        synsets = _wn.synsets(term)

        seen_labels = set()

        for synset in synsets:
            # Synonyms
            try:
                for lemma in synset.lemmas():
                    label = lemma.name().replace("_", " ")
                    # Skip echo of the original term and duplicates
                    if label.lower() == term.lower() or label in seen_labels:
                        continue
                    seen_labels.add(label)

                    results.append({
                        "label": label,
                        "source": "wordnet",
                        "type": "synonym",
                        "description": synset.definition(),
                        "score": 0.6,  # keep original scoring
                    })
            except Exception:
                # keep going; other synsets may still work
                pass

            # Hypernyms
            try:
                for hyper in synset.hypernyms():
                    for lemma in hyper.lemmas():
                        label = lemma.name().replace("_", " ")
                        if label in seen_labels:
                            continue
                        seen_labels.add(label)

                        results.append({
                            "label": label,
                            "source": "wordnet",
                            "type": "hypernym",
                            "description": hyper.definition(),
                            "score": 0.5,  # keep original scoring
                        })
            except Exception:
                pass

    except Exception as e:
        logger.error(f"❌ WordNet query failed for term '{term}': {e}")

    return results