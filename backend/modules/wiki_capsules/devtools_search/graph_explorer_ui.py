"""
🕸️ Graph Explorer UI Stub
--------------------------
Simple programmatic interface for exploring and previewing KG capsules.
"""

from backend.modules.wiki_capsules.integration.kg_query_extensions import get_wiki, list_domain


def explore_domain(domain: str = "Lexicon"):
    """List all entries in a domain."""
    return list_domain(domain)


def preview_capsule(domain: str, lemma: str):
    """Retrieve and preview capsule snippet."""
    entry = get_wiki(lemma, domain)
    capsule_text = entry.get("capsule", "")
    return "\n".join(capsule_text.splitlines()[:10])