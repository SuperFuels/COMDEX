# File: backend/modules/symbolgraph/symbolgraph_adapter.py

import logging
from typing import Dict, Optional

from backend.modules.symbolnet.symbolnet_loader import get_semantic_vector
from backend.modules.symbolgraph.symbolgraph_store import store_measurement_result

logger = logging.getLogger(__name__)


class SymbolGraphAdapter:
    """
    Adapter class for interfacing with SymbolGraph components.
    Handles semantic bias retrieval and symbolic feedback injection.
    """
    def __init__(self):
        self.bias_cache: Dict[str, list[float]] = {}

    def get_bias_vector(self, label: str) -> Optional[list[float]]:
        """
        Retrieve a semantic bias vector for a given glyph label.
        If previously fetched, returns cached result.

        Args:
            label (str): Glyph label to query.

        Returns:
            Optional[list[float]]: Semantic vector or None if unavailable.
        """
        try:
            if label in self.bias_cache:
                return self.bias_cache[label]
            vec = get_semantic_vector(label)
            if vec:
                self.bias_cache[label] = vec
                return vec
            return None
        except Exception as e:
            logger.warning(f"[SymbolGraph] Failed to fetch bias vector for '{label}': {e}")
            return None

    def push_measurement(self, glyph_id: str, collapse_value: str, score: float):
        """
        Push the result of a symbolic collapse or wave measurement into the SymbolGraph
        for learning and bias adaptation.

        Args:
            glyph_id (str): The glyph identifier being collapsed.
            collapse_value (str): Result of the collapse.
            score (float): Confidence or importance score of this event.
        """
        try:
            store_measurement_result(
                glyph_id=glyph_id,
                result=collapse_value,
                score=score
            )
            logger.info(f"[SymbolGraph] 📥 Recorded collapse for {glyph_id} -> {collapse_value} (score={score})")
        except Exception as e:
            logger.warning(f"[SymbolGraph] ⚠️ Failed to record collapse for {glyph_id}: {e}")


# ✅ Global singleton instance of adapter
_adapter = SymbolGraphAdapter()


# 🔌 Exposed functions for external use (used in wave kernels, etc.)

def get_bias_vector(label: str) -> Optional[list[float]]:
    """
    Public access to bias vector using global adapter.
    """
    return _adapter.get_bias_vector(label)


def push_measurement(glyph_id: str, collapse_value: str, score: float):
    """
    Public access to push symbolic measurement into SymbolGraph.
    """
    return _adapter.push_measurement(glyph_id, collapse_value, score)