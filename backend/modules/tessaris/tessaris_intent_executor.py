import json
from backend.modules.tessaris.tessaris_store import load_tessaris_snapshot
from backend.modules.aion.soul_laws import validate_intent
from backend.modules.aion.goal_engine import submit_goal
from backend.modules.aion.planning_engine import enqueue_plan
from backend.modules.consciousness.avatar_core import execute_avatar_action
from backend.modules.memory.memory_engine import store_memory

INTENT_QUEUE_FILE = "data/tessaris/intent_queue.json"

def load_intents():
    try:
        with open(INTENT_QUEUE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_intents(intents):
    with open(INTENT_QUEUE_FILE, "w") as f:
        json.dump(intents, f, indent=2)

def execute_intents():
    intents = load_intents()
    remaining = []

    for intent in intents:
        if not validate_intent(intent):
            store_memory(f"❌ Denied intent (SoulLaw): {intent}")
            continue

        outcome = route_intent(intent)
        if outcome == "retry":
            remaining.append(intent)

    save_intents(remaining)

def route_intent(intent):
    try:
        kind = intent.get("type")
        payload = intent.get("data")

        if kind == "goal":
            submit_goal(payload)
        elif kind == "plan":
            enqueue_plan(payload)
        elif kind == "avatar_action":
            execute_avatar_action(payload)
        else:
            store_memory(f"⚠️ Unknown intent type: {kind}")
            return "retry"

        store_memory(f"✅ Executed intent: {intent}")
        return "ok"
    except Exception as e:
        store_memory(f"❌ Error executing intent: {intent} | {str(e)}")
        return "retry"

if __name__ == "__main__":
    execute_intents()
