import json
from datetime import datetime

class StateManager:
    def __init__(self):
        self.identity = {
            "name": "AION",
            "version": "1.0",
            "created_by": "Kevin Robinson",
            "created_on": str(datetime.utcnow()),
        }
        self.context = {
            "location": "cloud",  # or 'phone', 'simulation', etc.
            "mode": "test",       # 'live', 'offline', etc.
            "environment": "development"
        }
        self.memory_snapshot = {}

    def get_identity(self):
        return self.identity

    def update_context(self, key, value):
        if key in self.context:
            self.context[key] = value
        else:
            print(f"[STATE] Unknown context key: {key}")

    def get_context(self):
        return self.context

    def save_memory_reference(self, snapshot):
        self.memory_snapshot = snapshot
        print("[STATE] Memory reference updated.")

    def dump_status(self):
        return {
            "identity": self.identity,
            "context": self.context,
            "memory_reference": self.memory_snapshot
        }

    def to_json(self):
        return json.dumps(self.dump_status(), indent=2)
