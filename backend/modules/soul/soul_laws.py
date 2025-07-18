import re
from backend.modules.memory.memory_engine import store_memory

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