# File: backend/modules/dna_chain/teleport.py

import os
import json
import datetime
from backend.modules.dna_chain.dna_registry import store_proposal
from backend.modules.dna_chain.switchboard import get_module_path
from backend.modules.dna_chain.dna_switch import DNA_SWITCH

# ✅ Import container loader + state
from backend.modules.consciousness.state_manager import STATE
from backend.modules.dimensions.dc_handler import load_dimension_by_id, load_dimension
from backend.modules.memory.memory_engine import store_memory

# ✅ DNA Switch Registration
DNA_SWITCH.register(__file__)

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

# --- 🔐 Navigation/Ethical Gate Logic (relaxed for now) ---
def ethical_gate_pass(container):
    return True  # ✅ relaxed gate for now

def has_permission(requester, container):
    return True  # ✅ allow all for now
# ----------------------------------------------------------

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

# Optional: Call once on boot (e.g., from consciousness_manager.py)
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
            print(f"[⛔] Navigation method 'teleport' not permitted from current container.")
            return "blocked_by_navigation"

        if not ethical_gate_pass(current_container):
            print("[🔒] Ethical gate prevents teleportation from this container.")
            return "blocked_by_ethics"

        if not has_permission(requester, current_container):
            print(f"[🔐] Requester '{requester}' lacks permission for this teleport.")
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
        print(f"[⚠️] Approval required – request stored in DNA Registry.")
        return "awaiting_approval"

    try:
        new_container = load_dimension_by_id(destination_key)
        if new_container:
            STATE.set_current_container(new_container)
            print(f"[🧭] Teleport successful: now in '{destination_key}' container.")
        else:
            raise ValueError(f"[⚠️] Dimension '{destination_key}' could not be loaded.")
    except Exception as e:
        print(f"[❌] Error during teleport load: {e}")
        print("[🛟] Attempting fallback container...")
        fallback_container = load_dimension_by_id("fallback")
        if fallback_container:
            STATE.set_current_container(fallback_container)
            return "fallback_loaded"
        else:
            print("[❌] Fallback container missing.")
            return "fatal_teleport_error"

    if route.get("gate_type") == "code":
        try:
            load_dimension(destination_key)
            print(f"[📦] Forward-loaded destination container: {destination_key}")
        except Exception as e:
            print(f"[⚠️] Could not forward-load destination container: {e}")

    store_memory({
        "type": "teleport_event",
        "source": source_key,
        "destination": destination_key,
        "trigger": "manual_teleport",
        "requester": requester,
        "reason": reason,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

    reverse_key = f"{destination_key}→{source_key}"
    if reverse_key not in registry:
        print(f"[🔁] Auto-adding reverse teleport from {destination_key} → {source_key}")
        register_teleport(destination_key, source_key, gate_type=route.get("gate_type", "code"))

    route["last_used"] = datetime.datetime.utcnow().isoformat()
    registry[route_key] = route
    save_teleport_registry(registry)

    print(f"[✅] Teleport from {source_key} → {destination_key} complete.")
    return "teleport_complete"

def list_routes():
    return load_teleport_registry()