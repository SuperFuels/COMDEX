# File: backend/modules/memory/memory_engine.py

from backend.modules.memory.compression import compress_text
import numpy as np
from typing import List, Dict

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# 🔹 In-memory vector database (temporary – replace with persistent DB later)
VECTOR_DB: List[Dict] = []
CONTAINER_MEMORY: Dict[str, Dict] = {}  # 🔄 Store loaded .dc containers here

def save_dream_vector(text: str) -> bool:
    """
    Compress a dream and store its embedding in memory.

    Args:
        text (str): Full dream text.

    Returns:
        bool: True if successfully stored.
    """
    embedding = compress_text(text)
    VECTOR_DB.append({
        "text": text[:300],  # Store a snippet of the original text
        "embedding": embedding.tolist()
    })
    print(f"🧠 Saved dream vector. Total stored: {len(VECTOR_DB)}")
    return True

def store_container_metadata(container: Dict) -> None:
    """
    Store .dc container metadata in memory.

    Args:
        container (dict): Loaded container dictionary.
    """
    cid = container.get("id", f"unknown_{len(CONTAINER_MEMORY)}")
    CONTAINER_MEMORY[cid] = container
    print(f"📦 Stored container '{cid}' in memory. Total: {len(CONTAINER_MEMORY)}")

def list_stored_containers() -> List[str]:
    """
    Returns a list of all container IDs currently in memory.
    """
    return list(CONTAINER_MEMORY.keys())

def get_container_by_id(container_id: str) -> Dict:
    """
    Retrieve stored container data by ID.

    Args:
        container_id (str): The ID of the container.

    Returns:
        dict: The container metadata, or empty dict if not found.
    """
    return CONTAINER_MEMORY.get(container_id, {})