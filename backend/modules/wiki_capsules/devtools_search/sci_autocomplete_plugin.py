"""
💡 SCI Autocomplete Plugin
--------------------------
Integrates with developer tools / IDEs to provide symbol and capsule name suggestions.
"""

from backend.modules.wiki_capsules.devtools_search.search_api import search_kg


def get_autocomplete_suggestions(prefix: str, domain: str = None, limit: int = 8):
    """Return autocomplete-style suggestions for given prefix."""
    if not prefix:
        return []
    results = search_kg(prefix, domain=domain, fuzzy=True, limit=limit)
    return [r["lemma"] for r in results]