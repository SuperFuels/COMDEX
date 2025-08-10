from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class AtomContainer:
    id: str
    kind: str
    title: str
    caps: List[str]
    requires: List[str] = field(default_factory=list)
    produces: List[str] = field(default_factory=list)
    links: List[Dict[str, str]] = field(default_factory=list)
    nodes: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    resources: Dict[str, Any] = field(default_factory=dict)
    viz: Dict[str, Any] = field(default_factory=dict)
    parent_container_id: Optional[str] = None

    # --- runtime ---
    def open(self, ctx: Dict[str, Any]) -> None:
        # lazy: prepare env, mount, image, etc. (stub hooks kept small)
        ctx.setdefault("opened_atoms", set()).add(self.id)

    def resolve(self, goal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decide if this atom can satisfy the goal.
        Returns a dict with 'score' and optional 'missing' requirement list.
        """
        score = 0.0
        tags = set(goal.get("tags", []))
        wants = set(goal.get("caps", []))
        score += len(set(self.caps) & wants) * 2.0
        score += len(set(self.tags) & tags) * 0.5
        # boost if goal node overlap
        goal_nodes = set(goal.get("nodes", []))
        score += len(set(self.nodes) & goal_nodes) * 1.0

        missing = [r for r in self.requires if r.endswith("?") is False and r not in goal]
        return {"score": score, "missing": missing}

    def export_pack(self) -> Dict[str, Any]:
        return {
            "id": self.id, "kind": self.kind, "caps": self.caps,
            "requires": self.requires, "produces": self.produces,
            "tags": self.tags, "nodes": self.nodes
        }