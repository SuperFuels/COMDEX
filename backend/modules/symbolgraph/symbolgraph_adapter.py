# backend/modules/symbolgraph/symbolgraph_adapter.py

import logging
from typing import Dict, Optional

from backend.modules.symbolnet.symbolnet_loader import get_semantic_vector
from backend.modules.symbolgraph.symbolgraph_store import store_measurement_result

logger = logging.getLogger(__name__)

class SymbolGraphAdapter:
    def __init__(self):
        self.bias_cache: Dict[str, list[float]] = {}

    def get_bias_vector(self, label: str) -> Optional[list[float]]:
        """
        Retrieve a semantic bias vector for a given glyph label.
        This can be used to influence wave amplitude during composition.
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
        Push the result of a wave collapse into the SymbolGraph for learning.
        """
        try:
            store_measurement_result(glyph_id=glyph_id, result=collapse_value, score=score)
            logger.info(f"[SymbolGraph] 📥 Recorded collapse for {glyph_id} → {collapse_value} (score={score})")
        except Exception as e:
            logger.warning(f"[SymbolGraph] ⚠️ Failed to record collapse for {glyph_id}: {e}")