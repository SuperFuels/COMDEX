from backend.modules.memory.compression import compress_text
import numpy as np
from typing import List, Dict

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# 🔹 In-memory vector database (temporary – replace with persistent DB later)
VECTOR_DB: List[Dict] = []

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
