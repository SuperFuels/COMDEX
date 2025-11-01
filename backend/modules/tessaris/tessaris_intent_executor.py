import json
import os
from datetime import datetime

from backend.modules.tessaris.tessaris_store import load_tessaris_snapshot
from backend.modules.soul.soul_laws import validate_intent
from backend.modules.consciousness.planning_engine import enqueue_plan
from backend.modules.avatar.avatar_core import execute_avatar_action
from backend.modules.hexcore.memory_engine import store_memory
from backend.modules.consciousness.state_manager import STATE
from backend.database import get_db
from backend.models.intent_log import IntentLog
from backend.modules.consciousness.memory_bridge import MemoryBridge

from time import perf_counter

# -----------------------------
# ✅ SCI overlay hook (safe stub)
# -----------------------------
try:
    from backend.modules.aion_language.sci_overlay import sci_emit
except Exception:
    def sci_emit(*a, **k): pass

INTENT_QUEUE_FILE = "data/tessaris/intent_queue.json"


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


def queue_tessaris_intent(intent):
    """External API wrapper for queuing an intent."""
    queue_intent(intent)


def execute_glyph_packet(packet):
    """Safe execution wrapper for glyph packets."""
    from backend.modules.tessaris.tessaris_engine import TessarisEngine  # Deferred
    engine = TessarisEngine()
    # ✅ Unified glyph execution adapter
    if hasattr(engine, "execute_packet"):
        return engine.execute_packet(packet)   # legacy

    if hasattr(engine, "execute_glyphs"):
        return engine.execute_glyphs(packet)   # modern final

    if hasattr(engine, "execute"):
        return engine.execute(packet)          # dispatcher variant

    if hasattr(engine, "interpret"):
        return engine.interpret(packet)        # symbolic interpreter

    raise AttributeError("TessarisEngine has no execution entrypoint for glyph packets")


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
        container_id = intent.get("container_id", "default")
        source = intent.get("source", "unknown")
        glyph = intent.get("glyph")

        t0 = perf_counter()

        if kind == "goal":
            from backend.modules.skills.goal_engine import submit_goal
            submit_goal(payload)
        elif kind == "plan":
            enqueue_plan(payload)
        elif kind == "avatar_action":
            execute_avatar_action(payload)
        else:
            store_memory(f"⚠️ Unknown intent type: {kind}")
            return "retry"

        dt = perf_counter() - t0
        store_memory(f"✅ Executed intent: {kind} in {dt:.3f}s - {payload}")
        log_intent(intent, "executed")

        # ✅ symbolic intent trace (after successful execution)
        sci_emit(
            "tessaris_intent",
            f"Intent executed: {kind} | glyph={glyph} | data={payload}"
        )

        memlog = MemoryBridge(container_id=container_id)
        memlog.log({
            "source": "tessaris_intent_executor",
            "event": "intent_executed",
            "intent_type": kind,
            "glyph": glyph,
            "payload": payload,
            "metadata": intent.get("metadata", {}),
            "duration": dt,
        })

        return "ok"
    except Exception as e:
        store_memory(f"❌ Error executing intent: {intent} | {str(e)}")
        log_intent(intent, "error")
        return "retry"


def scan_snapshot_for_intents(snapshot_path):
    try:
        snapshot = load_tessaris_snapshot(snapshot_path)
        glyphs = snapshot.get("glyphs", [])

        for glyph in glyphs:
            if isinstance(glyph, str) and glyph.strip().startswith("⟦"):
                # Attempt symbolic parse
                parsed = parse_symbolic_glyph(glyph)
                if not parsed:
                    continue

                intent_type = parsed["type"].lower()
                intent_value = {
                    "tag": parsed.get("tag"),
                    "value": parsed.get("value"),
                    "action": parsed.get("action"),
                }

                structured = {
                    "type": intent_type,
                    "data": intent_value,
                    "source": snapshot_path,
                    "timestamp": datetime.utcnow().isoformat(),
                    "glyph": glyph,
                    "container_id": parsed.get("container_id", "default")
                }
                queue_intent(structured)
                store_memory(f"📥 Scanned intent from snapshot: {structured}")
    except Exception as e:
        store_memory(f"⚠️ Failed to scan snapshot for intents: {str(e)}")


def parse_symbolic_glyph(glyph: str) -> dict | None:
    try:
        inner = glyph.strip("⟦⟧").strip()
        parts = inner.split("->")
        left = parts[0].strip()
        action = parts[1].strip() if len(parts) > 1 else "Reflect"
        type_tag, value = left.split(":", 1)
        g_type, tag = type_tag.split("|", 1)
        return {
            "type": g_type.strip(),
            "tag": tag.strip(),
            "value": value.strip(),
            "action": action
        }
    except Exception:
        return None


if __name__ == "__main__":
    execute_intents()