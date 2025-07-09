# File: backend/modules/tessaris/tessaris_intent.py

from typing import List, Dict, Any
from datetime import datetime
import uuid

class TessarisIntent:
    def __init__(self, intent_type: str, glyph: str, description: str, metadata: Dict[str, Any] = {}):
        self.id = str(uuid.uuid4())
        self.intent_type = intent_type  # e.g., "goal", "boot_skill"
        self.glyph = glyph
        self.description = description
        self.metadata = metadata
        self.timestamp = datetime.utcnow().isoformat()
        self.status = "pending"  # or "approved", "rejected", "executed"

    def to_dict(self):
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


# Global intent queue (for now)
TESSARIS_INTENTS: List[TessarisIntent] = []

def add_intent(intent: TessarisIntent):
    TESSARIS_INTENTS.append(intent)
    print(f"[🌱] New TessarisIntent queued: {intent.intent_type} → {intent.description}")

def list_intents(status_filter: str = None) -> List[Dict[str, Any]]:
    if status_filter:
        return [i.to_dict() for i in TESSARIS_INTENTS if i.status == status_filter]
    return [i.to_dict() for i in TESSARIS_INTENTS]

def update_intent_status(intent_id: str, new_status: str):
    for i in TESSARIS_INTENTS:
        if i.id == intent_id:
            i.status = new_status
            print(f"[🔁] Intent {intent_id} marked as {new_status}")
            return True
    return False
