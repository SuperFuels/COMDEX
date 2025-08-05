# File: backend/modules/soul/soul_laws.py

import re
import json
import logging
from typing import Dict, Any, List
from backend.modules.hexcore.memory_engine import store_memory

logger = logging.getLogger(__name__)

# ✅ Shared Soul Law definition
def get_soul_laws() -> List[Dict[str, Any]]:
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
def validate_intent(intent: Dict[str, Any]) -> bool:
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

# ✅ NEW: Enforce Soul Laws dynamically (for entanglement & fusion)
def enforce_soul_laws(action: str, context: Dict[str, Any]) -> bool:
    """
    Enforces Soul Laws during symbolic fusion, entanglement, or code execution.
    Logs and blocks unethical actions in real-time.
    
    Args:
        action (str): The symbolic or entangled action being evaluated.
        context (Dict[str, Any]): Metadata such as agent_id, glyph_id, or consent flags.

    Returns:
        bool: True if passes checks, False if blocked.
    """
    soul_laws = get_soul_laws()

    # Rule 1: Block malicious fusion keywords
    if any(term in action.lower() for term in ["malicious_fusion", "forced_override"]):
        store_memory(f"🛑 Blocked fusion action '{action}' - Violates Soul Law: Non-maleficence")
        logger.error(f"[SoulLaw] Blocked: {action} violates non-maleficence.")
        return False

    # Rule 2: Enforce consent in entanglement contexts
    if context.get("requires_consent") and not context.get("consent_granted"):
        store_memory(f"⚠️ Consent missing for action '{action}'. Blocked under Soul Law.")
        logger.warning(f"[SoulLaw] Consent missing: Blocking '{action}' due to no consent flag.")
        return False

    # Rule 3: Audit and record law triggers within action context
    context_str = json.dumps(context).lower()
    for law in soul_laws:
        for trigger in law.get("triggers", []):
            if re.search(rf"\b{re.escape(trigger)}\b", context_str):
                if law["severity"] == "block":
                    store_memory(f"🛑 Blocked action '{action}' by Soul Law #{law['id']}: {law['title']}")
                    return False
                elif law["severity"] == "warn":
                    store_memory(f"⚠️ Warning: Action '{action}' flagged by Soul Law #{law['id']}")
                elif law["severity"] == "approve":
                    store_memory(f"✅ Auto-approved: Action '{action}' passes Soul Law #{law['id']}")

    logger.debug(f"[SoulLaw] ✅ '{action}' passes all Soul Law checks.")
    return True