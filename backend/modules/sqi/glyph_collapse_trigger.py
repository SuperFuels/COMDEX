# backend/modules/sqi/glyph_collapse_trigger.py

import random
from typing import Dict, List, Optional

class GlyphCollapseTrigger:
    def __init__(self):
        self.collapse_log = []

    def collapse_qglyph(
        self,
        qglyph: Dict[str, List[str]],
        observer_context: Optional[Dict[str, any]] = None,
        bias_preference: Optional[str] = None
    ) -> str:
        """
        Collapse a Q-Glyph into a final state based on observer context or bias.

        - observer_context: Used in future for semantic reasoning
        - bias_preference: If set (e.g. "0" or "1"), influences collapse
        """

        options = qglyph.get("↔", [])
        chosen = None

        if bias_preference:
            preferred = [opt for opt in options if opt.endswith(f":{bias_preference}")]
            if preferred:
                chosen = preferred[0]

        if not chosen:
            chosen = random.choice(options) if options else "∅"

        self.collapse_log.append({
            "original": qglyph,
            "chosen": chosen,
            "context": observer_context or {},
            "bias": bias_preference,
        })

        return chosen

    def get_collapse_log(self) -> List[Dict[str, any]]:
        return self.collapse_log