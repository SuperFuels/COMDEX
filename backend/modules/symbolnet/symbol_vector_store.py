import os
import logging
import numpy as np
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

VECTOR_PATH = "symbolnet_data/numberbatch-en-19.08.txt"

class SymbolVectorStore:
    def __init__(self, path: str = VECTOR_PATH):
        self.path = path
        self.vectors: Dict[str, np.ndarray] = {}
        self.dim: Optional[int] = None
        self.loaded = False

    def load_vectors(self):
        if not os.path.exists(self.path):
            logger.error(f"❌ ConceptNet vector file not found at: {self.path}")
            return

        logger.info(f"📦 Loading ConceptNet vectors from: {self.path}")
        with open(self.path, "r", encoding="utf-8") as f:
            header = f.readline()
            for line in f:
                parts = line.strip().split(" ")
                label = parts[0].replace("/c/en/", "")
                try:
                    vector = np.array([float(x) for x in parts[1:]], dtype=np.float32)
                    self.vectors[label] = vector
                    if self.dim is None:
                        self.dim = len(vector)
                except ValueError:
                    logger.warning(f"⚠️ Skipping malformed vector line for label: {label}")

        logger.info(f"✅ Loaded {len(self.vectors)} semantic vectors ({self.dim} dims)")
        self.loaded = True

    def get(self, label: str) -> Optional[List[float]]:
        if not self.loaded:
            self.load_vectors()
        label = label.lower().replace("_", "-")
        vec = self.vectors.get(label)
        if vec is not None:
            norm = np.linalg.norm(vec)
            if norm > 0:
                return (vec / norm).tolist()
            return vec.tolist()
        logger.debug(f"🔍 No vector found for label: {label}")
        return None

# Singleton store for global use
symbol_vector_store = SymbolVectorStore()

def get_semantic_vector(label: str) -> Optional[List[float]]:
    return symbol_vector_store.get(label)