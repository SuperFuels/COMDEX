"""
🔎 Wiki DevTools Search API
---------------------------
Provides keyword and fuzzy search over the Knowledge Graph registry.
"""

import json
import re
from pathlib import Path
from difflib import get_close_matches
from typing import List, Dict, Any

KG_PATH = Path("data/knowledge/kg_registry.json")


def _load_registry() -> Dict[str, Any]:
    if not KG_PATH.exists():
        return {}
    return json.load(open(KG_PATH, "r", encoding="utf-8"))


def search_kg(keyword: str, domain: str = None, fuzzy: bool = True, limit: int = 10) -> List[Dict[str, Any]]:
    """Search the Knowledge Graph registry by keyword or lemma (optionally fuzzy)."""
    reg = _load_registry()
    results = []

    domains = [domain] if domain else reg.keys()
    keyword_lower = keyword.lower()

    for dom in domains:
        for lemma, data in reg.get(dom, {}).items():
            score = 0
            if keyword_lower in lemma.lower():
                score += 3
            if keyword_lower in json.dumps(data).lower():
                score += 1
            if score > 0:
                results.append({"domain": dom, "lemma": lemma, "score": score})

    if not results and fuzzy:
        # Fuzzy fallback
        candidates = []
        for dom in domains:
            candidates += list(reg.get(dom, {}).keys())
        close = get_close_matches(keyword, candidates, n=limit)
        for lemma in close:
            results.append({"domain": domain or "unknown", "lemma": lemma, "score": 0.5})

    # Sort by descending score
    return sorted(results, key=lambda x: x["score"], reverse=True)[:limit]