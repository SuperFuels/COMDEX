# ================================================================
# 🧮 QArray - Numeric array wrapper
# ================================================================
import numpy as np

class QArray:
    """Wrapper for NumPy arrays that supports symbolic linking."""
    def __init__(self, data):
        self.data = np.array(data, dtype=float)

    def mean(self):
        return self.data.mean()

    def __repr__(self):
        return f"QArray(shape={self.data.shape})"