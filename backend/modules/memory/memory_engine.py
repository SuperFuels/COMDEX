from backend.modules.memory.compression import compress_text
import numpy as np

# Simple in-memory vector store (replace with DB later)
VECTOR_DB = []

def save_dream_vector(text: str):
    """
    Compress and store the dream embedding.
    """
    embedding = compress_text(text)
    VECTOR_DB.append({
        "text": text[:300],
        "embedding": embedding.tolist()
    })
    print(f"🧠 Saved dream vector. Total stored: {len(VECTOR_DB)}")
    return True
