"""
💡 Wiki ↔ Photon Integration - Phase 3
--------------------------------------
Registers the 📚 glyph as a Photon plugin.
When a Photon script encounters 📚Domain>Lemma, this plugin
resolves the corresponding Wiki capsule from the Knowledge Graph.
"""

import logging
from backend.modules.wiki_capsules.integration.kg_query_extensions import get_wiki, list_domain

logger = logging.getLogger(__name__)

#───────────────────────────────────────────────
# 📚 Glyph Handler
#───────────────────────────────────────────────
def handle_wiki(instruction: str) -> dict:
    """
    Resolve a 📚 glyph reference such as '📚Lexicon>Apple'.

    Returns:
        dict containing lemma, domain, meta, and capsule text.
    """
    try:
        # Strip prefix & parse path
        if not instruction.startswith("📚"):
            raise ValueError("Invalid Wiki glyph call.")
        path = instruction[1:]
        parts = path.split(">", 1)
        domain = parts[0] if len(parts) > 1 else "Lexicon"
        lemma = parts[1] if len(parts) > 1 else parts[0]

        entry = get_wiki(lemma, domain)
        logger.info(f"[Photon📚] Resolved {domain}>{lemma}")
        return entry

    except Exception as e:
        logger.error(f"[Photon📚] Failed to resolve {instruction}: {e}")
        return {"error": str(e), "instruction": instruction}


#───────────────────────────────────────────────
# 🧠 Registration Hook
#───────────────────────────────────────────────
def register_with_photon(photon_executor):
    """
    Register 📚 handler into Photon's plugin registry.
    Expected to be called from photon_executor initialization.
    """
    try:
        photon_executor.register_plugin("📚", handle_wiki)
        logger.info("[Photon📚] Registered Wiki glyph handler.")
    except Exception as e:
        logger.error(f"[Photon📚] Registration failed: {e}")


#───────────────────────────────────────────────
# 🧪 CLI Utility
#───────────────────────────────────────────────
if __name__ == "__main__":
    # Simple manual test
    logging.basicConfig(level=logging.INFO)
    sample = "📚Lexicon>Apple"
    result = handle_wiki(sample)
    print("Result:", result)