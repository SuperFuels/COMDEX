# backend/modules/holo/hst_ir.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HSTNode:
    id: str
    kind: str
    label: Optional[str] = None
    language: Optional[str] = None
    props: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HSTEdge:
    id: str
    src: str
    dst: str
    kind: str = "semantic"


@dataclass
class HoloSemanticTree:
    """
    Very lightweight semantic tree.

    For now:
      - we treat the whole program as a single "program" node
      - optional child nodes for top-level items (if the caller passes any)
    Later you can evolve this without breaking the callers.
    """
    id: str                     # e.g. "hst:container/<cid>/t=0/v1"
    container_id: str
    language: str

    nodes: List[HSTNode] = field(default_factory=list)
    edges: List[HSTEdge] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)