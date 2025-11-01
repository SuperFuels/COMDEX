# ============================================================
# 📗 backend/modules/wiki_capsules/validation_maintenance/reference_validator.py
# ============================================================
"""
Reference Validator - Cross-Link and Entanglement Consistency Checker
---------------------------------------------------------------------
Ensures all entangled_links and cross-domain references exist within the KG registry.
"""

import json
from pathlib import Path
from backend.modules.wiki_capsules.integration.kg_query_extensions import _load_registry


def validate_cross_references() -> dict:
    """
    Validate that all entangled_links refer to existing capsules in the KG.

    Returns
    -------
    dict
        {
            "checked_domains": [...],
            "missing": [ { "source": "Lexicon>apple", "missing": "Lexicon>banana" }, ... ],
            "valid": bool
        }
    """
    reg = _load_registry()
    missing_refs = []

    for domain, entries in reg.items():
        for lemma, entry in entries.items():
            # handle both legacy and current formats
            meta = entry.get("meta", {})
            entangled = meta.get("entangled_links") or entry.get("entangled_links", {})

            if not entangled:
                continue

            for key, ref in entangled.items():
                # Normalize ref form
                if isinstance(ref, list):
                    for r in ref:
                        ref_domain, ref_lemma = _parse_reference(domain, r)
                        if not _exists_in_registry(reg, ref_domain, ref_lemma):
                            missing_refs.append({
                                "source": f"{domain}>{lemma}",
                                "missing": f"{ref_domain}>{ref_lemma}",
                            })
                else:
                    ref_domain, ref_lemma = _parse_reference(domain, ref)
                    if not _exists_in_registry(reg, ref_domain, ref_lemma):
                        missing_refs.append({
                            "source": f"{domain}>{lemma}",
                            "missing": f"{ref_domain}>{ref_lemma}",
                        })

    return {
        "checked_domains": list(reg.keys()),
        "missing": missing_refs,
        "valid": len(missing_refs) == 0,
    }


# ────────────────────────────────────────────────
# 🔧 Internal Helpers
# ────────────────────────────────────────────────
def _parse_reference(default_domain: str, ref: str) -> tuple[str, str]:
    """Split 'Domain>Lemma' safely with fallback to current domain."""
    if ">" in ref:
        ref_domain, ref_lemma = ref.split(">", 1)
        return ref_domain.strip(), ref_lemma.strip()
    return default_domain, ref.strip()


def _exists_in_registry(registry: dict, domain: str, lemma: str) -> bool:
    """Check if a lemma exists within the given domain."""
    return domain in registry and lemma in registry[domain]