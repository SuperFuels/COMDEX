# backend/modules/sqi/sqi_tessaris_bridge.py

# ── Lightweight SQI route chooser (goal → atoms/containers) ──────────────────
from typing import Dict, Any, List, Optional
from backend.modules.dimensions.universal_container_system.ucs_runtime import (
    ucs_runtime,  # singleton UCS runtime
)

def choose_route(goal: Dict[str, Any], k: int = 3) -> Dict[str, Any]:
    """
    goal example:
    {
      "id": "prove_theorem_X",
      "caps": ["lean.replay", "proof.graph"],
      "tags": ["math", "proof"],
      "nodes": ["logic_core"],
      "budget": 1.0
    }
    """
    # Greedy selection via UCS
    atom_ids = ucs_runtime.compose_path(goal, k=k)
    return {
        "goal_id": goal.get("id"),
        "atoms": atom_ids,
        "plan": [{"atom_id": a, "mode": "sequential"} for a in atom_ids],
    }

def execute_route(plan: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a simple sequential plan produced by choose_route().
    Looks up atoms via ucs_runtime.atom_index:
      atom_index[atom_id] -> (container_name, atom_dict)  OR  dict with refs (depending on runtime impl)
    Adapter dispatch is a placeholder to avoid code loss; swap in tool adapters later.
    """
    out: Dict[str, Any] = {"steps": [], "ok": True}

    for step in plan.get("plan", []):
        atom_id = step.get("atom_id")
        tup = ucs_runtime.atom_index.get(atom_id)

        if not tup:
            out["steps"].append({"atom_id": atom_id, "status": "missing"})
            out["ok"] = False
            continue

        # Support either tuple index style or dict with fields — keep non-breaking.
        container_name: Optional[str] = None
        atom_obj: Any = None
        if isinstance(tup, tuple) and len(tup) == 2:
            container_name, atom_obj = tup
        elif isinstance(tup, dict):
            container_name = tup.get("container") or tup.get("container_id")
            atom_obj = tup.get("ref") or tup.get("atom") or tup

        try:
            # TODO: dispatch by capability (e.g., "lean.replay" → Lean adapter)
            produced = {"kg_links": [], "produces": {}}
            out["steps"].append(
                {
                    "atom_id": atom_id,
                    "container": container_name,
                    "status": "ok",
                    "produced": produced,
                }
            )
        except Exception as e:
            out["ok"] = False
            out["steps"].append(
                {
                    "atom_id": atom_id,
                    "container": container_name,
                    "status": "error",
                    "error": str(e),
                }
            )

    return out


# ── Existing SQI ↔ Tessaris bridge (kept intact; no code loss) ───────────────
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
            entangled.append(
                {
                    "original": branch,
                    "qglyphs": qglyphs,
                }
            )

        return entangled

    def collapse_qpath(self, qpath: Dict, bias: Optional[str] = None) -> Dict:
        """
        Collapse a Q-path into a single resolved symbolic thought.
        """
        resolved: Dict[str, Any] = {}
        for key, qglyph in qpath["qglyphs"].items():
            resolved[key] = self.collapser.collapse_qglyph(
                qglyph, observer_context=None, bias_preference=bias
            )
        return resolved

    def execute_superposed_reasoning(
        self, root_thought: Dict, bias: Optional[str] = None
    ) -> List[Dict]:
        """
        Full pipeline: Expand → Entangle → Collapse → Return Resolved Thought Paths
        """
        branches = self.generate_q_thought_branches(root_thought)
        resolved_branches = []

        for qpath in branches:
            resolved = self.collapse_qpath(qpath, bias=bias)
            resolved_branches.append(resolved)

        return resolved_branches