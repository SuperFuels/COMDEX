from sentence_transformers import SentenceTransformer
import numpy as np

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# Load a lightweight embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

def compress_text(text: str) -> np.ndarray:
    """
    Convert text to a compressed vector embedding.
    """
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding

def compare_embeddings(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.
    """
    return float(np.dot(vec1, vec2))
