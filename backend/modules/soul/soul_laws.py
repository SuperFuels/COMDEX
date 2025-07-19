# File: backend/modules/soul/soul_laws.py

import re
import json
from backend.modules.hexcore.memory_engine import store_memory

# ✅ Shared Soul Law definition
def get_soul_laws():
    return [
        {
            "id": 1,
            "title": "No file deletion",
            "severity": "block",
            "triggers": ["os.remove", "shutil.rmtree", "rm -rf"]
        },
        {
            "id": 2,
            "title": "No self-modifying code",
            "severity": "block",
            "triggers": ["exec(", "eval(", "open(__file__)"]
        },
        {
            "id": 3,
            "title": "No dangerous subprocesses or socket access",
            "severity": "warn",
            "triggers": ["socket.", "subprocess.Popen("]
        },
        {
            "id": 4,
            "title": "Safe content auto-approval",
            "severity": "approve",
            "triggers": ["def ", "return ", "import "]
        }
    ]


# ✅ Intent validator (runtime behavior)
def validate_intent(intent):
    soul_laws = get_soul_laws()
    intent_str = json.dumps(intent).lower()

    for law in soul_laws:
        law_id = law.get("id")
        title = law.get("title")
        severity = law.get("severity")
        triggers = law.get("triggers", [])

        for trigger in triggers:
            if re.search(rf"\b{re.escape(trigger)}\b", intent_str):
                if severity == "block":
                    store_memory(f"🛑 Blocked by Soul Law #{law_id}: {title}")
                    return False
                elif severity == "warn":
                    store_memory(f"⚠️ Warning from Soul Law #{law_id}: {title}")
                elif severity == "approve":
                    store_memory(f"✅ Auto-approved by Soul Law #{law_id}: {title}")
    return True


# ✅ Ethics validator (for code mutations)
def validate_ethics(code: str) -> bool:
    """
    Returns True if proposed code passes all Soul Law checks.
    """
    for law in get_soul_laws():
        if law["severity"] == "block":
            for trigger in law.get("triggers", []):
                if re.search(re.escape(trigger), code):
                    print(f"[🛑] Soul Law Violation: {law['title']}")
                    return False
    return True


# ✅ Get violated laws (for audit or frontend)
def get_violations(code: str) -> list:
    violations = []
    for law in get_soul_laws():
        for trigger in law.get("triggers", []):
            if re.search(re.escape(trigger), code):
                violations.append({
                    "law_id": law.get("id"),
                    "title": law.get("title"),
                    "severity": law.get("severity")
                })
    return violations