# File: backend/modules/dimensions/dc_handler.py

import os
import json
from datetime import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

from backend.modules.memory.memory_engine import (
    CONTAINER_MEMORY,
    store_container_metadata,
    list_stored_containers,
    store_memory  # ✅ Added for logging teleport events
)

from backend.modules.dna_chain.teleport import teleport

DIMENSION_DIR = os.path.join(os.path.dirname(__file__), "../dimensions")

def list_containers_with_memory_status():
    containers = []
    for file in os.listdir(DIMENSION_DIR):
        if file.endswith(".dc.json"):
            container_id = file.replace(".dc.json", "")
            containers.append({
                "id": container_id,
                "in_memory": container_id in CONTAINER_MEMORY
            })
    return containers

def list_available_containers():
    stored = set(list_stored_containers())
    containers = []

    for file in os.listdir(DIMENSION_DIR):
        if file.endswith(".dc.json"):
            container_id = file.replace(".dc.json", "")
            containers.append({
                "id": container_id,
                "loaded": container_id in stored,
                "in_memory": container_id in CONTAINER_MEMORY
            })

    return containers

def validate_dimension(data):
    required_fields = ["id", "name", "description", "created_on", "dna_switch"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"[⚠️] Missing required field: {field}")
    return True

def load_dimension(container_id):
    filename = f"{container_id}.dc.json"
    path = os.path.join(DIMENSION_DIR, filename)

    if not os.path.exists(path):
        raise FileNotFoundError(f"[❌] Dimension container '{container_id}' not found at {path}")

    with open(path, "r") as f:
        data = json.load(f)

    # ✅ Validate structure
    validate_dimension(data)

    # ✅ Store metadata in memory
    store_container_metadata(data)

    print(f"[📦] Loaded dimension: {data['name']} (ID: {data['id']})")

    # ✅ Auto-teleport if navigation section defines it
    navigation = data.get("navigation", {})
    next_target = navigation.get("next")
    auto = navigation.get("auto_teleport", False)

    if auto and next_target:
        print(f"[🧭] Auto-teleporting to next dimension: {next_target}")
        teleport(container_id, next_target, reason="Auto-navigation trigger")

        # ✅ Log teleport event to memory
        store_memory({
            "type": "teleport_event",
            "source": container_id,
            "destination": next_target,
            "trigger": "auto_teleport",
            "timestamp": datetime.utcnow().isoformat()
        })

    return data

def load_and_validate(container_id):
    return load_dimension(container_id)  # Already does both