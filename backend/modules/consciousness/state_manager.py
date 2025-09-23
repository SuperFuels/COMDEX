# File: backend/modules/consciousness/state_manager.py
"""
📄 state_manager.py

🧭 State Manager (UCS Runtime, Container Orchestration & Context Control)
Handles universal container state, memory snapshots, vault decryption, personality gating, 
runtime time-tracking, and WebSocket sync across AION’s UCS runtime.

Design Rubric:
- 🧭 UCS Runtime Context .................... ✅
- 📦 Container Load/Activation ............. ✅
- 🔒 Vault Decryption + Trait Gates ........ ✅
- ⏱️ TimeController Tick & Tracking ........ ✅
- 🧠 Memory & Knowledge Graph Hooks ........ ✅
- 🌐 WebSocket Minimap & Event Broadcast ... ✅
- 🔁 Pause/Resume Runtime Control .......... ✅
- 📜 Agent State Persistence & Telemetry ... ✅
- 💾 Secure Glyph Injection & Save ........ ✅
- 🔗 Lean Container & Personality Engine ... ✅
"""

import os
import json
import hashlib
from datetime import datetime
import asyncio  # ✅ Coroutine handling
import threading  # ✅ Pause/resume lock

from backend.modules.validation.validator import validate_logic_trees
errors = validate_logic_trees(container)
container["validation_errors"] = ...
container["validation_errors_version"] = "v1"

# ✅ Lean container support
from backend.modules.lean.lean_utils import (
    is_lean_container,
    is_lean_universal_container_system
)

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

# GlyphVault integration
from backend.modules.glyphvault.container_vault_manager import ContainerVaultManager

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
        self.state = {}
        self.agent_states = self.load_agent_states()
        self.current_container = None
        self.loaded_containers = {}
        self.time_controller = TIME  # ⏳ Container time logic

        from backend.modules.glyphvault.key_manager import get_encryption_key

        encryption_key = get_encryption_key(
            default_fallback=b'\x00' * 32
        )  # ⚠️ fallback only for dev/test
        self.vault_manager = ContainerVaultManager(encryption_key)

        # ✅ Runtime pause flag
        self.paused = False
        self.pause_lock = threading.Lock()

    # ──────────────────────────────
    # ✅ Safe Active UCS Fetcher
    # ──────────────────────────────
    def get_active_universal_container_system(self) -> dict:
        """
        Safely returns the active Universal Container System (UCS) context.
        This enables lazy loading from other modules without direct imports.
        """
        return {
            "active_container": self.current_container,
            "loaded_containers": self.loaded_containers,
            "identity": self.identity,
            "context": self.context,
            "vault_manager": self.vault_manager,
            "time_controller": self.time_controller,
        }

    def get_avatar_state(self):
        """Return the current avatar state if available."""
        return self.state.get("avatar", {})

    # ──────────────────────────────
    # ✅ Pause/Resume Control
    # ──────────────────────────────
    def pause(self):
        with self.pause_lock:
            self.paused = True
            self.time_controller.pause_all()
            if WS:
                asyncio.ensure_future(WS.broadcast({"event": "state_paused"}))
            print("[⏸️] StateManager paused")

    def resume(self):
        with self.pause_lock:
            self.paused = False
            self.time_controller.resume_all()
            if WS:
                asyncio.ensure_future(WS.broadcast({"event": "state_resumed"}))
            print("[▶️] StateManager resumed")

    def is_paused(self):
        with self.pause_lock:
            return self.paused

    # ──────────────────────────────
    # ✅ Agent State Persistence
    # ──────────────────────────────
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

    # ──────────────────────────────
    # ✅ Identity & Context Updates
    # ──────────────────────────────
    def get_identity(self):
        return self.identity

    def update_context(self, key, value):
        self.context[key] = value
        print(f"[STATE] Context updated: {key} = {value}")

    # ──────────────────────────────
    # ✅ Secure Container Load + Gates
    def secure_load_and_set(self, container_id: str):
        try:
            # ✅ Load standard or lean container
            container = load_dimension(container_id)

            # ✅ Lean container detection
            if is_lean_container(container) or container.get("metadata", {}).get("origin") == "lean_import":
                MEMORY({
                    "type": "lean_container_loaded",
                    "container_id": container_id,
                    "logic_type": container.get("metadata", {}).get("logic_type", "unknown"),
                    "timestamp": datetime.utcnow().isoformat()
                })

                # 🔍 NEW: Validate lean containers + push into MemoryBridge
                try:
                    from backend.modules.lean.lean_validator import validate_lean_container
                    errors = validate_lean_container(container)
                    if errors:
                        container["validation_errors"] = errors
                except Exception as ve:
                    container["validation_errors"] = [
                        {"code": "lean_validation_failed", "message": str(ve)}
                    ]

                from backend.modules.consciousness.memory_bridge import MemoryBridge
                mb = MemoryBridge(container_id=container_id)
                mb({
                    "type": "lean_theorem",
                    "container_id": container_id,
                    "metadata": container.get("metadata", {}),
                    "timestamp": datetime.utcnow().isoformat()
                })

            # 🔒 Decrypt vault glyph data if present
            encrypted_glyph_blob = container.get("encrypted_glyph_data")
            if encrypted_glyph_blob:
                avatar_state = self.get_agent_state("AION")  # TODO: use dynamic current avatar id if needed
                success = self.vault_manager.load_container_glyph_data(
                    encrypted_glyph_blob,
                    avatar_state=avatar_state
                )
                if not success:
                    raise PermissionError(json.dumps({
                        "code": "vault_decryption_failed",
                        "message": "Vault decryption denied due to avatar state"
                    }))

            # ⚖️ SoulLaw / trait gates
            gates = container.get("gates", {})
            required_traits = gates.get("traits", {})
            for trait, required in required_traits.items():
                actual = PERSONALITY.get(trait, 0.0)
                if actual < required:
                    error_payload = {
                        "code": "trait_gate_denied",
                        "message": f"Trait '{trait}' below required: {actual} < {required}",
                        "trait": trait,
                        "required": required,
                        "actual": actual
                    }
                    # Log denial into MEMORY
                    MEMORY({
                        "type": "access_denied",
                        "container_id": container_id,
                        "issue": error_payload["message"],
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    # NEW: Broadcast denial via WS / CodexHUD
                    if WS:
                        asyncio.ensure_future(WS.broadcast({
                            "event": "trait_gate_denied",
                            "data": error_payload
                        }))
                    raise PermissionError(json.dumps(error_payload))

            # ✅ Register + activate
            self.loaded_containers[container_id] = container
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

    # ──────────────────────────────
    # ✅ Activate Loaded Container
    # ──────────────────────────────
    def set_current_container(self, container: dict):
        self.current_container = container
        print(f"[STATE] Current container set to: {container.get('id', 'unknown')}")

        # ✅ Normalize container type
        ctype = "unknown"
        if container.get("id", "").startswith("dc_"):
            ctype = "dc"
        elif container.get("id", "").startswith("lean_"):
            ctype = "lean"
        elif container.get("id", "").startswith("sec_"):
            ctype = "sec"
        elif container.get("id", "").startswith("ucs_"):
            ctype = "ucs"
        container["metadata"] = container.get("metadata", {})
        container["metadata"]["normalized_type"] = ctype

        # ✅ Run validation and attach results (A73 polish)
        try:
            from backend.modules.validation.validator import validate_logic_trees
            errors = validate_logic_trees(container)
            container["validation_errors"] = errors if isinstance(errors, list) else []
            container["validation_errors_version"] = "v1"
        except Exception as e:
            container["validation_errors"] = [{"code": "validation_failed", "message": str(e)}]
            container["validation_errors_version"] = "v1"

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

        # ✅ Prefetch child containers
        children = container.get("children", [])
        for child_id in children:
            child_path = os.path.join(DIMENSION_DIR, f"{child_id}.dc.json")
            if os.path.exists(child_path):
                with open(child_path, "r") as f:
                    child = json.load(f)

                    # NEW: validate prefetched container
                    try:
                        from backend.modules.lean.lean_validator import validate_lean_container
                        errors = validate_lean_container(child)
                        if errors:
                            child["validation_errors"] = errors
                    except Exception:
                        pass

                    MEMORY({
                        "role": "system",
                        "type": "container_prefetch",
                        "content": f"📦 Preloaded child container: {child.get('id')}"
                    })

                    # NEW: Push summary to KG
                    try:
                        from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
                        kg_writer = get_kg_writer()
                        kg_writer.inject_glyph(
                            content=child.get("id"),
                            glyph_type="container_prefetch",
                            metadata={"validation_errors": child.get("validation_errors", [])}
                        )
                    except Exception as kg_err:
                        print(f"[KG] Prefetch KG push failed: {kg_err}")

        # ✅ Consolidated WebSocket broadcast
        if WS:
            try:
                loop = asyncio.get_event_loop()
                cubes = container.get("cubes", {})
                glyph_summary = {g: 0 for g in ["⚙", "🧠", "🔒", "🌐"]}
                for cube in cubes.values():
                    glyph = cube.get("glyph")
                    if glyph in glyph_summary:
                        glyph_summary[glyph] += 1

                payload = {
                    "event": "container_switch",
                    "data": {
                        "id": container.get("id"),
                        "name": container.get("name", ""),
                        "timestamp": str(datetime.utcnow()),
                        "glyphs": glyph_summary,
                        "validation_errors": container.get("validation_errors", []),
                        "sqi_summary": container.get("sqi_summary", {})
                    }
                }
                asyncio.ensure_future(WS.broadcast(payload)) if loop.is_running() else loop.run_until_complete(WS.broadcast(payload))

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

    from backend.modules.consciousness.memory_bridge import MemoryBridge
    MEMORY_BRIDGE = MemoryBridge(container_id="state_manager")

    def save_memory_reference(self, snapshot):
        self.memory_snapshot = snapshot
        print("[STATE] Memory reference updated.")

        # ✅ Mirror into MemoryBridge with typed tag
        MEMORY_BRIDGE({
            "type": "state_snapshot",
            "snapshot": snapshot,
            "timestamp": datetime.utcnow().isoformat()
        })

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

            # Validate glyph syntax before saving
            from backend.modules.glyphos.glyph_validator import validate_glyph_syntax
            for glyph in glyphs:
                if not validate_glyph_syntax(glyph):
                    print(f"[ERROR] Invalid glyph syntax: {glyph}")
                    return False

            injected_coords = []
            for i, glyph in enumerate(glyphs):
                x = max_x + i + 1
                coord = f"{x},{base_yzt}"
                cubes[coord] = {
                    "coord": [x, 0, 0, 0],
                    "glyph": glyph,
                    "source": source,
                    "timestamp": str(datetime.utcnow())
                }
                injected_coords.append(coord)

            # Encrypt and store glyph data vault before saving container
            try:
                encrypted_blob = self.vault_manager.save_container_glyph_data(cubes)
                self.current_container["encrypted_glyph_data"] = encrypted_blob
            except Exception as vault_err:
                print(f"[ERROR] Vault save failed: {vault_err}. Rolling back glyph injection.")
                # Rollback injected glyphs
                for coord in injected_coords:
                    cubes.pop(coord, None)
                return False

            # Optionally remove plaintext cubes for security
            # self.current_container["cubes"] = {}

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
    
    def get_current_container(self):
        return self.current_container

    def get_current_container_id(self):
        if self.current_container:
            return self.current_container.get("id")
        return None

    def container_exists(self, container_id: str) -> bool:
        """Check if a container is available in the current loaded or disk state."""
        if container_id in self.loaded_containers:
            return True
        container_path = os.path.join(DIMENSION_DIR, f"{container_id}.dc.json")
        return os.path.exists(container_path)

# ✅ Singleton
STATE = StateManager()


# ✅ Load container from .dc.json file for benchmark/test usage
def load_container_from_file(file_path: str) -> dict:
    """
    Loads a .dc container file from disk into current state.
    Returns the loaded container dict.
    Raises an exception if load fails.
    """
    with open(file_path, "r") as f:
        data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(f"[❌] Loaded data is not a valid container dict: {type(data)}")
        STATE.set_current_container(data)
        STATE.loaded_containers[data.get("id", "unknown")] = data
        print(f"[📦] Loaded container: {data.get('id', 'unknown')}")
        return data

# 🔄 Exports
def get_agent_state(agent_id):
    return STATE.get_agent_state(agent_id)

def update_agent_state(agent_id, updates):
    return STATE.update_agent_state(agent_id, updates)

# ✅ Local dummy fallback for test/CLI contexts
class DummyStateManager:
    def __init__(self):
        self._current_container_id = None

    def set_status(self, *args, **kwargs): pass
    def update_progress(self, *args, **kwargs): pass
    def log_event(self, *args, **kwargs): pass
    def reset(self): pass

    def get_current_container(self):
        return self._current_container_id

    def set_current_container(self, container_id: str):
        self._current_container_id = container_id

# ✅ Global instance for compatibility
state_manager = StateManager()