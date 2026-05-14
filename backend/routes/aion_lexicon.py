# File: backend/routes/aion_lexicon.py
# 📚 AION Resonance Lexicon + Semantic Comparison API

from fastapi import APIRouter
import json, os
from backend.modules.aion_resonance.lexicon_reasoner import relate_terms

router = APIRouter()
BOOT_PATH = "backend/modules/aion_resonance/boot_config.json"


@router.get("/lexicon")
async def get_lexicon():
    """
    Return the current learned resonance lexicon (Φ signatures per keyword).
    """
    if not os.path.exists(BOOT_PATH):
        return {"status": "empty", "lexicon": {}}
    with open(BOOT_PATH, "r") as f:
        data = json.load(f)
    return {"status": "ok", "lexicon": data}


@router.get("/lexicon/compare")
async def compare_terms(a: str, b: str):
    """
    Compare two Φ terms semantically using resonance similarity.
    Example:
      /api/aion/lexicon/compare?a=gratitude&b=error
    """
    result = relate_terms(a, b)
    return result