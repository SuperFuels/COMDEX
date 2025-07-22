# backend/modules/glyphos/mutation_checker.py
# 🧪 Mutation compliance checker against Soul Laws

import re
from typing import List, Dict
from backend.modules.soul.soul_laws import get_soul_laws

def check_mutation_against_soul_laws(diff_text: str) -> List[Dict]:
    """
    Evaluate mutation diff against defined Soul Laws.
    Returns a list of violations with law metadata if any are found.
    """
    violations = []
    laws = get_soul_laws()

    for law in laws:
        for trigger in law.get("triggers", []):
            if re.search(rf"\b{re.escape(trigger)}\b", diff_text, re.IGNORECASE):
                violations.append({
                    "law_id": law["id"],
                    "title": law["title"],
                    "trigger": trigger,
                    "severity": law.get("severity", "medium")
                })

    return violations