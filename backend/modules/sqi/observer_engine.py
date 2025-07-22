# backend/modules/sqi/observer_engine.py

import random
from typing import Dict, Any
from .entangler_engine import is_entangled, resolve_entanglement

class ObserverEngine:
    def __init__(self):
        self.collapse_log = []

    def observe_and_collapse(self, glyph_id: str, state: Dict[str, Any], context: Dict[str, Any]) -> str:
        """
        Observe a Q-Glyph and deterministically or probabilistically collapse it.
        Returns the collapsed glyph state.
        """
        entangled_ids = resolve_entanglement(glyph_id)
        collapse_result = {}

        for eid in entangled_ids:
            glyph_state = state.get(eid, "superposed")
            collapse_to = self._collapse_logic(eid, glyph_state, context)
            state[eid] = collapse_to
            collapse_result[eid] = collapse_to
            self.collapse_log.append({
                "glyph_id": eid,
                "collapsed_to": collapse_to,
                "context": context,
            })

        return collapse_result.get(glyph_id, "collapsed")

    def _collapse_logic(self, glyph_id: str, glyph_state: str, context: Dict[str, Any]) -> str:
        """
        Basic contextual collapse logic.
        Future: plug in Lumara's ethics filter or intent weighting.
        """
        if "bias" in context:
            bias = context["bias"]
            if isinstance(bias, dict) and glyph_id in bias:
                return bias[glyph_id]

        # Default: 50/50 collapse
        return random.choice(["0", "1"])

    def get_collapse_log(self):
        return self.collapse_log