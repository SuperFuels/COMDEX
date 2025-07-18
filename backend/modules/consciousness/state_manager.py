import os
import json
import hashlib
from datetime import datetime
import asyncio  # ✅ Coroutine handling

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

# ✅ Memory injection
from backend.modules.hexcore.memory_engine import MEMORY, store_memory, store_container_metadata

# ✅ WebSocket push
try:
    from backend.modules.websocket_manager import WebSocketManager
    WS = WebSocketManager()
except Exception:
    WS = None  # fallback if not available

# ✅ Secure loading
from backend.modules.dna_chain.dc_handler import load_dimension, load_dimension_by_file, get_dc_path
from backend.modules.consciousness.personality_engine import PROFILE as PERSONALITY

# ⏳ Time tracking
from backend.modules.dimensions.time_controller import TimeController
TIME = TimeController()

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
        self.loaded_containers = {}
        self.time_controller = TIME  # ⏳ Container time logic

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
            container = load_dimension(container_id)

            gates = container.get("gates", {})
            required_traits = gates.get("traits", {})
            for trait, required in required_traits.items():
                actual = PERSONALITY.get(trait, 0.0)
                if actual < required:
                    MEMORY({
                        "type": "access_denied",
                        "container_id": container_id,
                        "issue": f"Trait '{trait}' below required: {actual} < {required}",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    raise PermissionError(f"[🔒] Trait gate locked: {trait} = {actual} < {required}")

            self.set_current_container(container)
            return True

        except Exception as e:
            MEMORY({
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
            "label": f"container:{container.get('id', 'unknown')}",
            "content": f"[📦] Container {container.get('name', 'unnamed')} activated."
        })

        # ⏳ Begin or resume time tracking for container
        container_id = container.get("id")
        if container_id:
            current_tick = self.time_controller.get_tick(container_id)
            print(f"[⏳] Container {container_id} time tick: {current_tick}")

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
                    MEMORY({
                        "role": "system",
                        "type": "container_prefetch",
                        "content": f"📦 Preloaded child container: {child.get('id')}"
                    })

        if WS:
            try:
                loop = asyncio.get_event_loop()
                payload = {
                    "event": "container_switch",
                    "data": {
                        "id": container.get("id"),
                        "name": container.get("name", ""),
                        "timestamp": str(datetime.utcnow())
                    }
                }
                asyncio.ensure_future(WS.broadcast(payload)) if loop.is_running() else loop.run_until_complete(WS.broadcast(payload))

                # ✅ Send minimap update too
                cubes = container.get("cubes", {})
                glyph_summary = {g: 0 for g in ["⚙", "🧠", "🔒", "🌐"]}
                for cube in cubes.values():
                    glyph = cube.get("glyph")
                    if glyph in glyph_summary:
                        glyph_summary[glyph] += 1
                minimap_payload = {
                    "event": "minimap_update",
                    "data": {
                        "id": container.get("id"),
                        "glyphs": glyph_summary,
                        "timestamp": str(datetime.utcnow())
                    }
                }
                asyncio.ensure_future(WS.broadcast(minimap_payload)) if loop.is_running() else loop.run_until_complete(WS.broadcast(minimap_payload))

            except Exception as e:
                print(f"[WS] Broadcast failed: {e}")

    def get_current_container_path(self):
        if not self.current_container:
            return None
        return get_dc_path(self.current_container)

    def get_context(self):
        if self.current_container:
            self.context["active_container"] = self.current_container
            container_id = self.current_container.get("id")
            if container_id:
                self.context["container_time"] = self.time_controller.get_status(container_id)
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

    def load_container_from_file(self, file_path: str):
        container = load_dimension_by_file(file_path)
        self.set_current_container(container)
        self.loaded_containers[container["id"]] = container
        return container

    def tick_current_container(self, state_snapshot: dict):
        if not self.current_container:
            return
        container_id = self.current_container.get("id")
        if container_id:
            self.time_controller.tick(container_id, state_snapshot)

    def write_glyph_to_cube(self, glyphs: list, source: str = "synthesis") -> bool:
        try:
            if not self.current_container:
                print("[ERROR] No container loaded.")
                return False

            if "cubes" not in self.current_container:
                self.current_container["cubes"] = {}

            cubes = self.current_container["cubes"]
            max_x = max([int(c.split(",")[0]) for c in cubes.keys()] + [0])
            base_yzt = "0,0,0"

            for i, glyph in enumerate(glyphs):
                x = max_x + i + 1
                coord = f"{x},{base_yzt}"
                cubes[coord] = {
                    "coord": [x, 0, 0, 0],
                    "glyph": glyph,
                    "source": source,
                    "timestamp": str(datetime.utcnow())
                }

            path = self.get_current_container_path()
            if path:
                with open(path, "w") as f:
                    json.dump(self.current_container, f, indent=2)
                print(f"[💾] Injected {len(glyphs)} glyph(s) into container at path {path}")

            if WS:
                loop = asyncio.get_event_loop()
                payload = {
                    "event": "glyph_injected",
                    "data": {
                        "glyphs": glyphs,
                        "container": self.current_container.get("id"),
                        "timestamp": str(datetime.utcnow())
                    }
                }
                asyncio.ensure_future(WS.broadcast(payload)) if loop.is_running() else loop.run_until_complete(WS.broadcast(payload))

            return True
        except Exception as e:
            print(f"[ERROR] write_glyph_to_cube failed: {e}")
            return False


# ✅ Singleton
STATE = StateManager()

# 🔄 Exports
def get_agent_state(agent_id):
    return STATE.get_agent_state(agent_id)

def update_agent_state(agent_id, updates):
    return STATE.update_agent_state(agent_id, updates)