"""
ObserverCore - Phase 40F (minimal)
----------------------------------
Embodied "attention-as-action" interface:
- Focus on a concept (attention = movement = collapse)
- Emit a focusing beam via Photon bridge
- Log focus history for later embodiment work
"""

import time, json, logging
from pathlib import Path
from backend.bridges.photon_AKG_bridge import PAB
from backend.modules.aion_knowledge import knowledge_graph_core as akg

logger = logging.getLogger(__name__)
FOCUS_LOG = Path("data/analysis/avatar_focus_log.jsonl")

class ObserverCore:
    def __init__(self):
        self.pose = {"position": [0,0,0], "gaze": None, "attention": None}
        self.history = []

    def focus(self, concept_id: str, strength: float = 0.7):
        """Direct attention to a concept; emit a focus beam and write AKG trace."""
        ts = time.time()
        self.pose["gaze"] = concept_id
        self.pose["attention"] = strength

        # Photon "focus" event
        PAB.emit({
            "timestamp": ts,
            "type": "attention_focus",
            "target": concept_id,
            "amplitude": strength,
            "phase": 0.0
        })

        # Trace in AKG
        akg.add_triplet(concept_id, "attended_at", str(ts), strength=strength)

        # Persist focus event
        FOCUS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(FOCUS_LOG, "a") as f:
            f.write(json.dumps({"time": ts, "concept": concept_id, "strength": strength}) + "\n")

        self.history.append((ts, concept_id, strength))
        logger.info(f"[Observer] Focused {concept_id} @ {strength:.2f}")
        return {"timestamp": ts, "concept": concept_id, "strength": strength}

# Global instance
try:
    AVATAR
except NameError:
    AVATAR = ObserverCore()
    print("👁️  ObserverCore global instance initialized as AVATAR")