# File: backend/modules/tessaris/tessaris_intent_executor.py

import json
import os
from datetime import datetime

from backend.modules.tessaris.tessaris_store import load_tessaris_snapshot
from backend.modules.aion.soul_laws import validate_intent
from backend.modules.aion.goal_engine import submit_goal
from backend.modules.aion.planning_engine import enqueue_plan
from backend.modules.consciousness.avatar_core import execute_avatar_action
from backend.modules.memory.memory_engine import store_memory
from backend.modules.consciousness.state_manager import STATE
from backend.database import get_db
from backend.models.intent_log import IntentLog
from backend.modules.memory.memory_bridge import MemoryBridge

INTENT_QUEUE_FILE = "data/tessaris/intent_queue.json"
memlog = MemoryBridge()


def load_intents():
    try:
        with open(INTENT_QUEUE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_intents(intents):
    os.makedirs(os.path.dirname(INTENT_QUEUE_FILE), exist_ok=True)
    with open(INTENT_QUEUE_FILE, "w") as f:
        json.dump(intents, f, indent=2)


def queue_intent(intent):
    intents = load_intents()
    intents.append(intent)
    save_intents(intents)
    store_memory(f"📝 Queued intent: {intent}")


def execute_intents():
    intents = load_intents()
    remaining = []

    for intent in intents:
        if not validate_intent(intent):
            store_memory(f"❌ Denied intent (SoulLaw): {intent}")
            log_intent(intent, "denied")
            continue

        outcome = route_intent(intent)
        if outcome == "retry":
            remaining.append(intent)

    save_intents(remaining)


def log_intent(intent, outcome):
    try:
        db = next(get_db())
        log = IntentLog(
            intent_type=intent.get("type", "unknown"),
            data=json.dumps(intent),
            outcome=outcome,
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        store_memory(f"🧾 Logged intent to DB: {log.intent_type} ({outcome})")
    except Exception as e:
        store_memory(f"⚠️ Failed to log intent to DB: {e}")


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
        log_intent(intent, "executed")

        # ✅ MemoryBridge trace logging
        memlog.log({
            "source": "tessaris_intent_executor",
            "event": "intent_executed",
            "intent_type": kind,
            "glyph": intent.get("glyph"),
            "payload": payload,
            "metadata": intent.get("metadata", {}),
        })

        return "ok"
    except Exception as e:
        store_memory(f"❌ Error executing intent: {intent} | {str(e)}")
        log_intent(intent, "error")
        return "retry"


# 🔍 Auto-scan from Tessaris branch snapshot

def scan_snapshot_for_intents(snapshot_path):
    try:
        snapshot = load_tessaris_snapshot(snapshot_path)
        glyphs = snapshot.get("glyphs", [])

        for glyph in glyphs:
            symbol = glyph.get("symbol", "")
            metadata = glyph.get("meta", {})

            if symbol == "⟦" and metadata.get("type") == "Intent":
                intent_type = metadata.get("tag", "")
                intent_value = metadata.get("value", {})

                structured = {
                    "type": intent_type.lower(),
                    "data": intent_value,
                    "source": snapshot_path,
                    "timestamp": datetime.utcnow().isoformat()
                }
                queue_intent(structured)
                store_memory(f"📥 Scanned intent from snapshot: {structured}")
    except Exception as e:
        store_memory(f"⚠️ Failed to scan snapshot for intents: {str(e)}")


if __name__ == "__main__":
    execute_intents()