# backend/modules/sqi/observer_engine.py

import random
from typing import Dict, Any
from backend.modules.sqi.entangler_engine import is_entangled, resolve_entanglement

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

    def observe_beam(self, beam_state: dict) -> None:
        """
        Compatibility method for QQC main loop.
        Observes a propagated SQI beam and logs or records its features.
        """
        try:
            beam_id = beam_state.get("beam_id", "unknown")
            coherence = beam_state.get("coherence")
            entropy = beam_state.get("entropy_drift")
            gain = beam_state.get("gain")

            print(f"[ObserverEngine] 🔭 Observed beam {beam_id} | coherence={coherence}, entropy={entropy}, gain={gain}")
            if hasattr(self, "record"):
                self.record(beam_state)
        except Exception as e:
            print(f"[ObserverEngine] ⚠️ observe_beam() failed: {e}")