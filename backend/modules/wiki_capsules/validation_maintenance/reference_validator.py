"""
🔗 Reference Validator — Cross-Link Integrity Checker
-----------------------------------------------------
Scans WikiCapsules to ensure all entangled_links refer to valid targets.
"""

import json
from pathlib import Path


def validate_references(registry_path: str = "data/knowledge/kg_registry.json") -> dict:
    """Validate that all entangled links resolve to existing lemmas in KG."""
    path = Path(registry_path)
    if not path.exists():
        return {"status": "error", "error": "KG registry not found."}

    registry = json.load(open(path, "r", encoding="utf-8"))
    errors = []

    for domain, entries in registry.items():
        for lemma, capsule in entries.items():
            entangled = capsule.get("entangled_links", {})
            for target_domain, links in entangled.items():
                for target in links:
                    if target_domain not in registry or target not in registry[target_domain]:
                        errors.append(
                            f"{domain}>{lemma} → missing link {target_domain}>{target}"
                        )

    return {"status": "ok" if not errors else "warn", "errors": errors}