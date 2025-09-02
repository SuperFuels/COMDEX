# File: backend/modules/symbolnet/symbolnet_vector_utils.py

import os
import numpy as np
from typing import Optional
from backend.modules.codex.symbolic_registry import symbolic_registry

# ✅ Constants
VECTOR_FILE = "backend/data/conceptnet/numberbatch-en-19.08.txt"
VECTOR_DIM = 300  # ConceptNet Numberbatch vectors are 300-dimensional

# ✅ Load the vectors once
_loaded_vectors = False

def load_vectors() -> None:
    """
    Load ConceptNet Numberbatch vectors into the symbolic_registry.
    Only runs once.
    """
    global _loaded_vectors
    if _loaded_vectors:
        return

    if not os.path.exists(VECTOR_FILE):
        print(f"[⚠️] Vector file not found: {VECTOR_FILE}. Semantic vectors will be unavailable.")
        _loaded_vectors = True
        return

    print(f"[🔢] Loading semantic vectors from {VECTOR_FILE} ...")
    with open(VECTOR_FILE, "r", encoding="utf-8") as f:
        first_line = f.readline()  # Skip header line
        for line in f:
            parts = line.strip().split()
            if len(parts) != VECTOR_DIM + 1:
                continue  # Skip malformed lines

            label = parts[0].lower().replace("/c/en/", "").replace("_", " ")
            vector = np.array(parts[1:], dtype=np.float32).tolist()

            # Inject into registry
            symbolic_registry.register(label, {"vector": vector})

    _loaded_vectors = True
    print(f"[✅] Loaded semantic vectors into registry: {len(symbolic_registry.registry)} entries.")


def get_semantic_vector(label: str) -> Optional[list[float]]:
    """
    Retrieve the semantic vector (Numberbatch or fallback) for a given label.
    Returns None if unavailable.
    """
    if not label:
        return None

    load_vectors()  # Ensure vectors are loaded
    entry = symbolic_registry.get(label.lower())
    if entry and "vector" in entry:
        return entry["vector"]

    return None