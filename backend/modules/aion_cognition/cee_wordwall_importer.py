# ================================================================
# 🌐 CEE Wordwall Importer — Phase 45G.12 (Tessaris Update)
# ================================================================
"""
Imports educational exercises from Wordwall’s oEmbed API.
Used to ground Aion’s symbolic cognition in real, human-designed test structures.

Enhancements:
  • Robust error handling + safe prompt normalization
  • Synthetic resonance metadata (ρ, I, SQI) for Cognition Engine
  • Structured fallback when metadata or text is missing
  • Ready for hybrid Wordwall ↔ LLM enrichment
"""

import requests
import logging
import random
import time
from bs4 import BeautifulSoup  # optional, for parsing embedded HTML

logger = logging.getLogger(__name__)
API = "https://wordwall.net/api/oembed"


# ------------------------------------------------------------
def _resonance():
    """Generate synthetic resonance parameters for testing."""
    ρ = round(random.uniform(0.6, 0.9), 3)
    I = round(random.uniform(0.8, 1.0), 3)
    SQI = round((ρ + I) / 2, 3)
    return {"ρ": ρ, "I": I, "SQI": SQI}


# ------------------------------------------------------------
def fetch_wordwall_metadata(resource_url: str):
    """Fetch oEmbed metadata and normalize core info."""
    try:
        params = {"url": resource_url, "format": "json"}
        resp = requests.get(API, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"[Wordwall] Fetch failed for {resource_url}: {e}")
        return None

    return {
        "title": data.get("title"),
        "author": data.get("author_name"),
        "html": data.get("html"),
        "thumbnail": data.get("thumbnail_url"),
        "provider": data.get("provider_name", "Wordwall"),
        "fetched_at": time.time(),
    }


# ------------------------------------------------------------
def extract_text_from_embed(embed_html: str | None):
    """Attempt to extract visible question text from embed HTML."""
    if not embed_html:
        return ""
    try:
        soup = BeautifulSoup(embed_html, "html.parser")
        text = soup.get_text(" ", strip=True)
        return text or ""
    except Exception as e:
        logger.warning(f"[Wordwall] HTML parse failed: {e}")
        return ""


# ------------------------------------------------------------
def wordwall_to_exercise(resource_url: str):
    """Convert a Wordwall resource into a normalized CEE exercise stub."""
    meta = fetch_wordwall_metadata(resource_url)
    if not meta:
        return {
            "type": "imported_wordwall",
            "prompt": "[Wordwall import failed]",
            "options": [],
            "answer": None,
            "resonance": _resonance(),
            "timestamp": time.time(),
            "meta": {"url": resource_url, "error": "metadata_unavailable"},
        }

    text = extract_text_from_embed(meta.get("html"))
    prompt_text = (text or meta.get("title") or "").strip()

    # --- Ensure safe prompt ---
    if not prompt_text:
        prompt_text = "[Wordwall exercise imported — no prompt text]"

    packet = {
        "type": "imported_wordwall",
        "prompt": prompt_text[:200] + ("..." if len(prompt_text) > 200 else ""),
        "options": [],            # options may be enriched by LLM later
        "answer": None,
        "resonance": _resonance(),
        "timestamp": time.time(),
        "meta": meta,
    }

    logger.info(f"[Wordwall] Imported exercise: {meta.get('title') or 'Untitled'}")
    return packet


# ------------------------------------------------------------
# 🚀 CLI Smoke-Test
# ------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    url = "https://wordwall.net/resource/39252"
    ex = wordwall_to_exercise(url)
    print(ex)