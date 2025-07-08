# File: backend/modules/consciousness/state_manager.py

import os
import json
import hashlib
from datetime import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

# ✅ Memory injection
from backend.modules.hexcore.memory_engine import MEMORY, store_memory

# ✅ WebSocket push
try:
    from backend.modules.websocket_manager import WebSocketManager
    WS = WebSocketManager()
except Exception:
    WS = None  # fallback if not available

# ✅ Secure loading
from backend.modules.dimensions.dc_handler import load_dimension
from backend.modules.skills.personality import PERSONALITY

STATE_FILE = "agent_state.json"
DIMENSION_DIR = os.path.join(os.path.dirname(__file__), "../dimensions")


class StateManager:
    def __init__(self):
        self.identity = {
            "name": "AION",
            "version": "1.0",
            "created_by": "Kevin Robinson",
            "created_on": str(datetime.utcnow()),
        }
        self.context = {
            "location": "cloud",
            "mode": "test",
            "environment": "development",
            "available_containers": []
        }
        self.memory_snapshot = {}
        self.agent_states = self.load_agent_states()
        self.current_container = None

    def load_agent_states(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        return {}

    def save_agent_states(self):
        with open(STATE_FILE, "w") as f:
            json.dump(self.agent_states, f, indent=2)

    def get_agent_state(self, agent_id):
        return self.agent_states.get(agent_id, {
            "location": "unknown",
            "teleport_history": []
        })

    def update_agent_state(self, agent_id, updates):
        state = self.get_agent_state(agent_id)
        state.update(updates)
        self.agent_states[agent_id] = state
        self.save_agent_states()

    def get_identity(self):
        return self.identity

    def update_context(self, key, value):
        self.context[key] = value
        print(f"[STATE] Context updated: {key} = {value}")

    def secure_load_and_set(self, container_id: str):
        try:
            container = load_dimension(container_id)  # ✅ Includes gate & hash checks

            # 🔐 Optional gate (legacy support)
            gates = container.get("gates", {})
            required_traits = gates.get("traits", {})

            for trait, required in required_traits.items():
                actual = PERSONALITY.get(trait, 0.0)
                if actual < required:
                    store_memory({
                        "type": "access_denied",
                        "container_id": container_id,
                        "issue": f"Trait '{trait}' below required: {actual} < {required}",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    raise PermissionError(f"[🔒] Trait gate locked: {trait} = {actual} < {required}")

            self.set_current_container(container)
            return True

        except Exception as e:
            store_memory({
                "type": "tamper_detected",
                "container_id": container_id,
                "issue": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            print(f"[SECURITY] Container load blocked: {e}")
            return False

    def set_current_container(self, container: dict):
        self.current_container = container
        print(f"[STATE] Current container set to: {container.get('id', 'unknown')}")

        MEMORY.store({
            "role": "system",
            "type": "container_change",
            "content": f"🧭 AION switched to container: {container.get('id')}"
        })

        try:
            from backend.modules.skills.goal_engine import GOALS
            GOALS.log_progress({
                "type": "environment",
                "event": "teleport",
                "message": f"Teleported to container: {container.get('id')}",
                "success": True
            })
        except Exception as e:
            print(f"[GOAL] Goal logging failed: {e}")

        self.update_context("last_teleport", {
            "id": container.get("id"),
            "timestamp": str(datetime.utcnow())
        })

        children = container.get("children", [])
        for child_id in children:
            child_path = os.path.join(DIMENSION_DIR, f"{child_id}.dc.json")
            if os.path.exists(child_path):
                with open(child_path, "r") as f:
                    child = json.load(f)
                    MEMORY.store({
                        "role": "system",
                        "type": "container_prefetch",
                        "content": f"📦 Preloaded child container: {child.get('id')}"
                    })

        if WS:
            try:
                WS.broadcast({
                    "event": "container_switch",
                    "data": {
                        "id": container.get("id"),
                        "name": container.get("name", ""),
                        "timestamp": str(datetime.utcnow())
                    }
                })
            except Exception as e:
                print(f"[WS] Broadcast failed: {e}")

    def get_context(self):
        if self.current_container:
            self.context["active_container"] = self.current_container
        return self.context

    def save_memory_reference(self, snapshot):
        self.memory_snapshot = snapshot
        print("[STATE] Memory reference updated.")

    def dump_status(self):
        return {
            "identity": self.identity,
            "context": self.get_context(),
            "memory_reference": self.memory_snapshot,
            "agents": self.agent_states,
            "current_container": self.current_container
        }

    def to_json(self):
        return json.dumps(self.dump_status(), indent=2)

    def list_containers_with_status(self):
        containers = []
        try:
            files = os.listdir(DIMENSION_DIR)
            for file in files:
                if file.endswith(".dc.json"):
                    container_id = file.replace(".dc.json", "")
                    is_loaded = (
                        self.current_container and
                        self.current_container.get("id") == container_id
                    )
                    containers.append({
                        "id": container_id,
                        "loaded": is_loaded
                    })
        except Exception as e:
            print(f"[ERROR] Listing containers failed: {str(e)}")
        return containers


# ✅ Singleton instance
STATE = StateManager()

# 🔄 Exported helpers
def get_agent_state(agent_id):
    return STATE.get_agent_state(agent_id)

def update_agent_state(agent_id, updates):
    return STATE.update_agent_state(agent_id, updates)