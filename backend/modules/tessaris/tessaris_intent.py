# File: backend/modules/tessaris/tessaris_intent.py

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
import os

from backend.modules.hexcore.memory_engine import store_memory
from backend.modules.consciousness.memory_bridge import MemoryBridge

INTENT_STORAGE_PATH = "data/tessaris/runtime_intents.json"


class TessarisIntent:
    def __init__(self, intent_type: str, glyph: str, description: str, metadata: Dict[str, Any] = {}):
        self.id = str(uuid.uuid4())
        self.intent_type = intent_type
        self.glyph = glyph
        self.description = description
        self.metadata = metadata
        self.timestamp = datetime.utcnow().isoformat()
        self.status = "pending"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "intent_type": self.intent_type,
            "glyph": self.glyph,
            "description": self.description,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "status": self.status,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TessarisIntent':
        intent = TessarisIntent(
            intent_type=data["intent_type"],
            glyph=data["glyph"],
            description=data["description"],
            metadata=data.get("metadata", {})
        )
        intent.id = data.get("id", str(uuid.uuid4()))
        intent.timestamp = data.get("timestamp", datetime.utcnow().isoformat())
        intent.status = data.get("status", "pending")
        return intent

    def __repr__(self):
        return f"<Intent {self.intent_type} | {self.glyph} | {self.status}>"

    def short(self) -> str:
        return f"{self.intent_type}: {self.glyph} -> {self.description}"


# In-memory queue
TESSARIS_INTENTS: List[TessarisIntent] = []


def add_intent(intent: TessarisIntent):
    # Avoid duplicates
    if any(i.glyph == intent.glyph and i.intent_type == intent.intent_type for i in TESSARIS_INTENTS):
        store_memory(f"⚠️ Duplicate intent skipped: {intent.short()}")
        return

    TESSARIS_INTENTS.append(intent)
    store_memory(f"🌱 Queued TessarisIntent: {intent.short()}")

    # Log to MemoryBridge
    container_id = intent.metadata.get("container_id", "default")
    MemoryBridge(container_id).log({
        "source": "tessaris_intent",
        "event": "intent_queued",
        "intent": intent.to_dict()
    })

    save_intents_to_disk()


def list_intents(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    if status_filter:
        return [i.to_dict() for i in TESSARIS_INTENTS if i.status == status_filter]
    return [i.to_dict() for i in TESSARIS_INTENTS]


def update_intent_status(intent_id: str, new_status: str) -> bool:
    for i in TESSARIS_INTENTS:
        if i.id == intent_id:
            i.status = new_status
            store_memory(f"🔁 Updated intent {intent_id} -> {new_status}")
            save_intents_to_disk()
            return True
    return False


def save_intents_to_disk():
    try:
        data = [i.to_dict() for i in TESSARIS_INTENTS]
        os.makedirs(os.path.dirname(INTENT_STORAGE_PATH), exist_ok=True)
        with open(INTENT_STORAGE_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        store_memory(f"⚠️ Failed to save intent state: {str(e)}")


def load_intents_from_disk():
    global TESSARIS_INTENTS
    try:
        if not os.path.exists(INTENT_STORAGE_PATH):
            return

        with open(INTENT_STORAGE_PATH, "r") as f:
            raw = json.load(f)
            TESSARIS_INTENTS = [TessarisIntent.from_dict(i) for i in raw]
            store_memory(f"💾 Restored {len(TESSARIS_INTENTS)} TessarisIntents from disk")
    except Exception as e:
        store_memory(f"⚠️ Failed to load intent state: {str(e)}")