from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_AKG = None

def get_akg():
    """
    Safe singleton accessor. Returns an AKGTripletStore or None.
    Never hard-fails the caller.
    """
    global _AKG
    if _AKG is not None:
        return _AKG

    try:
        from backend.modules.aion_cognition.akg_triplets import AKGTripletStore
        _AKG = AKGTripletStore()
        return _AKG
    except Exception as e:
        logger.warning("[AKG] unavailable (continuing): %s", e)
        _AKG = None
        return None


def reinforce_answer_is(prompt: str, answer: str, hit: float = 1.0) -> bool:
    """
    Convenience: reinforce (prompt, answer_is, answer).
    Returns True if reinforced, False if skipped.
    """
    akg = get_akg()
    if akg is None:
        return False

    try:
        akg.reinforce(prompt, "answer_is", answer, hit=float(hit))
        akg.save()
        return True
    except Exception as e:
        logger.warning("[AKG] reinforce failed (continuing): %s", e)
        return False