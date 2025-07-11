import os
import json
import datetime
from backend.modules.dna_chain.dna_registry import register_proposal
from backend.modules.dna_chain.switchboard import get_module_path
from backend.modules.dna_chain.dna_switch import DNA_SWITCH

# ✅ DNA Switch Registration
DNA_SWITCH.register(__file__)

# ✅ Import container loader + state
from backend.modules.dna_chain.dc_handler import (
    handle_object_interaction,
    load_dimension_by_id,
    load_dimension
)
from backend.modules.consciousness.state_manager import STATE
from backend.modules.hexcore.memory_engine import MEMORY

TELEPORT_DB_PATH = os.path.join(os.path.dirname(__file__), "teleport_registry.json")

def load_teleport_registry():
    if not os.path.exists(TELEPORT_DB_PATH):
        return {}
    with open(TELEPORT_DB_PATH, "r") as f:
        return json.load(f)

def save_teleport_registry(data):
    with open(TELEPORT_DB_PATH, "w") as f:
        json.dump(data, f, indent=2)

def register_teleport(source_key, destination_key, gate_type="code", requires_approval=False):
    registry = load_teleport_registry()
    route_key = f"{source_key}→{destination_key}"
    if route_key in registry:
        return  # Skip if already exists

    registry[route_key] = {
        "source": source_key,
        "destination": destination_key,
        "gate_type": gate_type,
        "requires_approval": requires_approval,
        "last_used": None
    }
    save_teleport_registry(registry)
    print(f"[🌀] Registered teleport from {source_key} → {destination_key}")

# --- 🔐 Navigation/Ethical Gate Logic ---
def ethical_gate_pass(container):
    return True  # Placeholder for moral/ethical checks

def has_permission(requester, container):
    return True  # Placeholder for role-based access

def trait_gate_pass(container, required_traits: dict) -> bool:
    traits = container.get("traits", {})
    for trait, minimum in required_traits.items():
        if traits.get(trait, 0) < minimum:
            return False
    return True

def key_gate_pass(container, memory_engine, required_keys: list) -> bool:
    keys = memory_engine.get_keys()  # Assumes this method returns list of held keys
    for rk in required_keys:
        if rk not in keys:
            return False
    return True
# ----------------------------------------

def initialize_teleports():
    register_teleport("aion_start", "fallback")
    register_teleport("fallback", "aion_start")
    register_teleport("aion_start", "jungle")
    register_teleport("jungle", "aion_start")
    register_teleport("aion_start", "lab")
    register_teleport("lab", "aion_start")
    register_teleport("jungle", "lab")
    register_teleport("lab", "jungle")
    register_teleport("jungle", "fallback")
    register_teleport("lab", "fallback")
    register_teleport("fallback", "jungle")
    register_teleport("fallback", "lab")

# Optional boot call
initialize_teleports()

def teleport(source_key, destination_key, reason, requester="AION"):
    registry = load_teleport_registry()
    route_key = f"{source_key}→{destination_key}"
    route = registry.get(route_key)

    if not route:
        print(f"[❌] No teleport route from {source_key} to {destination_key}")
        return "no_route"

    current_container = STATE.get_current_container()
    if current_container:
        nav_methods = current_container.get("navigation", {}).get("methods", [])
        if "teleport" not in nav_methods:
            print(f"[⛔] Navigation method 'teleport' not permitted.")
            return "blocked_by_navigation"

        if not ethical_gate_pass(current_container):
            print("[🔒] Ethical gate prevents teleportation.")
            return "blocked_by_ethics"

        if not has_permission(requester, current_container):
            print(f"[🔐] Requester '{requester}' lacks permission.")
            return "blocked_by_permission"

    if route.get("requires_approval"):
        proposal = {
            "proposal_id": f"teleport_{source_key}_{destination_key}_{datetime.datetime.utcnow().isoformat()}",
            "file": f"{source_key} → {destination_key}",
            "reason": reason,
            "replaced_code": "N/A",
            "new_code": "N/A",
            "diff": "Teleport Request",
            "approved": False,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "teleport_type": route["gate_type"],
            "requested_by": requester
        }
        store_proposal(proposal)
        print(f"[⚠️] Approval required — request stored.")
        return "awaiting_approval"

    try:
        new_container = load_dimension_by_id(destination_key)
        if not new_container:
            raise ValueError("Null container")

        required_traits = new_container.get("gate_lock", {}).get("traits_required", {})
        if required_traits and not trait_gate_pass(new_container, required_traits):
            print(f"[🔐] Gate lock triggered — traits missing.")
            MEMORY.log_gate_lock(destination_key, required_traits)
            return "gate_lock_failed"

        required_keys = new_container.get("gate_lock", {}).get("keys_required", [])
        if required_keys and not key_gate_pass(new_container, MEMORY, required_keys):
            print(f"[🔑] Gate lock triggered — key(s) missing: {required_keys}")
            MEMORY.log_gate_lock(destination_key, {"missing_keys": required_keys})
            return "key_gate_failed"

        expected_hash = new_container.get("hash", "")
        if expected_hash and not expected_hash.startswith("safe_"):
            print(f"[⚠️] Hash mismatch or unsafe content.")
            MEMORY.log_tamper_detected(destination_key, "Checksum validation failed")
            return "tamper_detected"

        STATE.set_current_container(new_container)
        MEMORY.log_container_loaded(destination_key)

    except Exception as e:
        print(f"[❌] Teleport error: {e}")
        print("[🛟] Attempting fallback...")
        fallback = load_dimension_by_id("fallback")
        if fallback:
            STATE.set_current_container(fallback)
            return "fallback_loaded"
        else:
            print("[❌] Fallback missing.")
            return "fatal_teleport_error"

    if route.get("gate_type") == "code":
        try:
            load_dimension(destination_key)
            print(f"[📦] Forward-loaded destination container: {destination_key}")
        except Exception as e:
            print(f"[⚠️] Could not forward-load: {e}")

    MEMORY.log_teleport_event(source_key, destination_key, trigger="manual")

    reverse_key = f"{destination_key}→{source_key}"
    if reverse_key not in registry:
        print(f"[🔁] Auto-adding reverse route: {destination_key} → {source_key}")
        register_teleport(destination_key, source_key, gate_type=route.get("gate_type", "code"))

    route["last_used"] = datetime.datetime.utcnow().isoformat()
    registry[route_key] = route
    save_teleport_registry(registry)

    print(f"[✅] Teleport complete: {source_key} → {destination_key}")
    return "teleport_complete"

def list_routes():
    return load_teleport_registry()