from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import logging

# ✅ Address registry + optional wormhole linker (safe fallbacks)
try:
    from backend.modules.aion.address_book import address_book
except Exception:  # pragma: no cover
    class _NullAB:
        def register_container(self, *_a, **_k): pass
    address_book = _NullAB()

try:
    from backend.modules.dna_chain.container_linker import link_wormhole
except Exception:  # pragma: no cover
    def link_wormhole(*_a, **_k): pass

# ✅ Hub connector helper (idempotent)
try:
    from backend.modules.dimensions.container_helpers import connect_container_to_hub
except Exception:  # pragma: no cover
    def connect_container_to_hub(*_a, **_k): pass

logger = logging.getLogger(__name__)


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

    # NEW: keep the full meta + an explicit address field
    meta: Dict[str, Any] = field(default_factory=dict)
    address: Optional[str] = None

    # --- runtime ---
    def open(self, ctx: Dict[str, Any]) -> None:
        # lazy: prepare env, mount, image, etc. (stub hooks kept small)
        ctx.setdefault("opened_atoms", set()).add(self.id)

        # ✅ Ensure this atom is discoverable via address book + wormhole graph (idempotent)
        try:
            self._register_address_and_link()
        except Exception as e:
            logger.warning(f"[AtomContainer] address/wormhole setup failed for {self.id}: {e}")

    def resolve(self, goal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decide if this atom can satisfy the goal.
        Returns a dict with 'score' and optional 'missing' requirement list.
        Heuristics:
          - Exact address match => big boost (or effectively a short-circuit)
          - caps ⊆ goal.caps (weighted)
          - tag overlap (small weight)
          - node overlap (medium weight)
        """
        score = 0.0
        reasons: List[str] = []

        # 0) exact address match (if goal provides one)
        goal_addr = (goal.get("address") or "").strip()
        if goal_addr and self.address and goal_addr == self.address:
            score += 100.0  # dominate other signals
            reasons.append(f"address=={self.address}")

        # 1) capability overlap
        wants = set(goal.get("caps", []))
        cap_hit = len(set(self.caps) & wants)
        if cap_hit:
            score += cap_hit * 2.0
            reasons.append(f"caps_overlap={cap_hit}")

        # 2) tag overlap
        tags = set(goal.get("tags", []))
        tag_hit = len(set(self.tags) & tags)
        if tag_hit:
            score += tag_hit * 0.5
            reasons.append(f"tags_overlap={tag_hit}")

        # 3) node overlap
        goal_nodes = set(goal.get("nodes", []))
        node_hit = len(set(self.nodes) & goal_nodes)
        if node_hit:
            score += node_hit * 1.0
            reasons.append(f"nodes_overlap={node_hit}")

        # 4) simple requires check (kept as before, but avoid false positives)
        missing = []
        for r in self.requires:
            if not r.endswith("?") and r not in goal:
                missing.append(r)
        if missing:
            reasons.append(f"missing={missing}")

        return {"score": score, "missing": missing, "explain": reasons}

    def export_pack(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "caps": self.caps,
            "requires": self.requires,
            "produces": self.produces,
            "tags": self.tags,
            "nodes": self.nodes,
            "address": self.address,   # NEW
            "meta": self.meta,         # NEW
        }

    # ---------- helpers ----------
    @classmethod
    def from_container(cls, container: Dict[str, Any]) -> "AtomContainer":
        """
        Build an AtomContainer from a .dc.json container dict.
        Pulls caps/tags/nodes/address from container.meta (non-breaking).
        """
        meta = container.get("meta") or {}
        title = meta.get("title") or container.get("id") or container.get("name") or "atom"

        atom = cls(
            id=container.get("id") or container.get("name") or title,
            kind=container.get("type", "atom"),
            title=title,
            caps=list(meta.get("caps", [])),
            requires=list(meta.get("requires", [])),
            produces=list(meta.get("produces", [])),
            links=list(meta.get("links", [])),
            nodes=list(meta.get("nodes", [])),
            tags=list(meta.get("tags", [])),
            resources=container.get("resources", {}),
            viz=container.get("viz", {}),
            parent_container_id=None,
            meta=meta,
            address=meta.get("address"),
        )

        # ✅ Eagerly register/link too (idempotent); if you prefer lazy, remove this and rely on open()
        try:
            atom._register_address_and_link()
        except Exception as e:
            logger.debug(f"[AtomContainer] from_container register/link skipped for {atom.id}: {e}")

        return atom

    # --- NEW INTERNAL: centralized address + wormhole hookup ---
    def _register_address_and_link(self, hub_id: str = "ucs_hub") -> None:
        """
        Ensure this atom is in the global address book and linked into the wormhole graph.
        Safe to call multiple times.
        """
        # minimal container-ish record for the directory
        record = {
            "id": self.id,
            "name": self.title or self.id,
            "type": self.kind,
            "address": self.address,
            "meta": self.meta,
            "caps": self.caps,
            "tags": self.tags,
            "nodes": self.nodes,
        }
        # keep original registration path
        address_book.register_container(record)

        # optional hub link (no-op if already linked or hub missing)
        try:
            link_wormhole(self.id, hub_id)
        except Exception:
            # keep silent in prod; the caller's try/except will decide logging level
            pass

        # ✅ NEW: centralized helper so this atom is connected to the HQ hub graphically
        try:
            doc = {
                "id": self.id,
                "name": self.title or self.id,
                "geometry": self.meta.get("geometry", "Unknown"),
                "type": self.kind,
                "meta": {"address": self.address or f"ucs://local/{self.id}#atom"},
            }
            connect_container_to_hub(doc)  # idempotent, safe
        except Exception as e:
            logger.debug(f"[AtomContainer] connect_container_to_hub skipped for {self.id}: {e}")