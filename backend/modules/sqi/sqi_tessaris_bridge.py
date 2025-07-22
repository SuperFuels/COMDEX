# backend/modules/sqi/sqi_tessaris_bridge.py

from typing import Dict, List, Optional
from backend.modules.tessaris.tessaris_engine import TessarisEngine
from backend.modules.sqi.qglyph_entangler import QGlyphEntangler
from backend.modules.sqi.glyph_collapse_trigger import GlyphCollapseTrigger

class SQITessarisBridge:
    def __init__(self, tessaris_engine: TessarisEngine):
        self.tessaris = tessaris_engine
        self.entangler = QGlyphEntangler()
        self.collapser = GlyphCollapseTrigger()

    def generate_q_thought_branches(self, root_thought: Dict) -> List[Dict]:
        """
        Expands a single Tessaris thought using Q-Glyph entanglement logic.
        Returns a list of possible superposed branches.
        """
        base_branches = self.tessaris.expand_thought_branch(root_thought)
        entangled = []

        for branch in base_branches:
            qglyphs = self.entangler.entangle(branch)
            entangled.append({
                "original": branch,
                "qglyphs": qglyphs
            })

        return entangled

    def collapse_qpath(self, qpath: Dict, bias: Optional[str] = None) -> Dict:
        """
        Collapse a Q-path into a single resolved symbolic thought.
        """
        resolved = {}
        for key, qglyph in qpath["qglyphs"].items():
            resolved[key] = self.collapser.collapse_qglyph(qglyph, observer_context=None, bias_preference=bias)
        return resolved

    def execute_superposed_reasoning(self, root_thought: Dict, bias: Optional[str] = None) -> List[Dict]:
        """
        Full pipeline: Expand → Entangle → Collapse → Return Resolved Thought Paths
        """
        branches = self.generate_q_thought_branches(root_thought)
        resolved_branches = []

        for qpath in branches:
            resolved = self.collapse_qpath(qpath, bias=bias)
            resolved_branches.append(resolved)

        return resolved_branches