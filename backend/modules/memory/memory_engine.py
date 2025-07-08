from backend.modules.memory.compression import compress_text
import numpy as np
from typing import List, Dict
from datetime import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# 🔹 In-memory vector database (temporary – replace with persistent DB later)
VECTOR_DB: List[Dict] = []
CONTAINER_MEMORY: Dict[str, Dict] = {}  # 🔄 Store loaded .dc containers here

def save_dream_vector(text: str) -> bool:
    """
    Compress a dream and store its embedding in memory.
    """
    embedding = compress_text(text)
    VECTOR_DB.append({
        "text": text[:300],
        "embedding": embedding.tolist()
    })
    print(f"🧠 Saved dream vector. Total stored: {len(VECTOR_DB)}")
    return True

def store_container_metadata(container: Dict) -> None:
    """
    Store .dc container metadata in memory.
    """
    cid = container.get("id", f"unknown_{len(CONTAINER_MEMORY)}")
    CONTAINER_MEMORY[cid] = container
    print(f"📦 Stored container '{cid}' in memory. Total: {len(CONTAINER_MEMORY)}")

def list_stored_containers() -> List[str]:
    return list(CONTAINER_MEMORY.keys())

def get_container_by_id(container_id: str) -> Dict:
    return CONTAINER_MEMORY.get(container_id, {})

# ✅ NEW: General memory logger
def store_memory(payload: Dict) -> None:
    """
    Logs a memory event to VECTOR_DB (to be replaced by real DB).
    """
    payload["timestamp"] = datetime.utcnow().isoformat()
    VECTOR_DB.append(payload)
    print(f"🧠 Memory logged: {payload.get('type')} — {payload.get('content', str(payload))[:80]}")

# ✅ NEW: Specialized loggers
def log_teleport_event(source_id: str, destination_id: str, trigger: str = "manual") -> None:
    store_memory({
        "type": "teleport_event",
        "role": "system",
        "source": source_id,
        "destination": destination_id,
        "trigger": trigger,
        "content": f"Teleported from {source_id} → {destination_id} via {trigger}"
    })

def log_gate_lock(container_id: str, required_traits: Dict) -> None:
    store_memory({
        "type": "gate_lock",
        "role": "system",
        "container": container_id,
        "content": f"Access denied to container '{container_id}' — required traits: {required_traits}"
    })

def log_tamper_detected(container_id: str, reason: str) -> None:
    store_memory({
        "type": "tamper_detected",
        "role": "system",
        "container": container_id,
        "content": f"Tamper detected in container '{container_id}': {reason}"
    })

def log_container_loaded(container_id: str) -> None:
    store_memory({
        "type": "container_loaded",
        "role": "system",
        "container": container_id,
        "content": f"Container '{container_id}' was loaded into memory."
    })