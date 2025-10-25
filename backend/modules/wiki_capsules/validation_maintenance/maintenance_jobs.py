"""
🕓 Maintenance Jobs — Automated Validation & Cleanup
---------------------------------------------------
Nightly validation routines for WikiCapsules and Knowledge Graph registry.
"""

import json
from datetime import datetime
from pathlib import Path
from backend.modules.wiki_capsules.validation_maintenance.wiki_linter import lint_capsule_file
from backend.modules.wiki_capsules.validation_maintenance.reference_validator import validate_references


LOG_PATH = Path("data/logs/wiki_validation.log")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def run_maintenance(root_path: str = "data/knowledge") -> dict:
    """Run all validation jobs and log results."""
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "lint": [],
        "refs": {},
    }

    for file in Path(root_path).rglob("*.wiki.phn"):
        results["lint"].append(lint_capsule_file(str(file)))

    results["refs"] = validate_references()

    with open(LOG_PATH, "a", encoding="utf-8") as log:
        log.write(json.dumps(results, indent=2) + "\n")

    print(f"[Maintenance] Completed at {results['timestamp']}")
    return results