# -*- coding: utf-8 -*-
# backend/modules/sqi/sqi_math_adapter.py
"""
Drift gap mapper: scans container logic entries, finds unresolved deps / admitted proofs,
and converts them into a DriftReport with DriftGaps.

Heuristics (simple, robust):
- missing dependency names in `depends_on` that do not exist in the same container
- any proof node with flags like {"admitted": true} or "proof_status": "incomplete"
- entries with empty/placeholder logic strings
- "TODO/???/admit" markers inside logic_raw/logic fields
"""
from __future__ import annotations
from typing import Dict, Any, List, Tuple, Set
from backend.modules.sqi.drift_types import DriftReport, DriftGap, DriftStatus

# utility to pick the active logic list
def _collect_logic_entries(container: Dict[str, Any]) -> List[Dict[str, Any]]:
    for f in ("symbolic_logic","expanded_logic","hoberman_logic","exotic_logic","symmetric_logic","axioms"):
        v = container.get(f)
        if isinstance(v, list): 
            return v
    return []

def _index_names(entries: List[Dict[str, Any]]) -> Set[str]:
    return {e.get("name") for e in entries if e.get("name")}

def _is_incomplete(entry: Dict[str, Any]) -> bool:
    flags = entry.get("flags") or {}
    if flags.get("admitted") or flags.get("incomplete"):
        return True
    ps = entry.get("proof_status")
    if isinstance(ps, str) and ps.lower() in {"admitted","incomplete","todo"}:
        return True
    # text sniff
    for k in ("logic_raw","logic"):
        s = entry.get(k)
        if isinstance(s, str) and any(tok in s.lower() for tok in ["todo","???","admit","sketch"]):
            return True
    return False

def _missing_deps(entry: Dict[str, Any], names: Set[str]) -> List[str]:
    deps = entry.get("depends_on") or []
    return [d for d in deps if d not in names]

def compute_drift(container: Dict[str, Any]) -> DriftReport:
    entries = _collect_logic_entries(container)
    names = _index_names(entries)

    gaps: List[DriftGap] = []
    total = 0.0

    for e in entries:
        name = e.get("name") or "unnamed"
        # 1) missing deps
        miss = _missing_deps(e, names)
        if miss:
            w = 1.0 + 0.25 * len(miss)
            gaps.append(DriftGap(
                name=name,
                reason="missing_dependencies",
                missing=miss,
                weight=w,
                hints=["Import/define these lemmas in container or adjust depends_on."]
            ))
            total += w
        # 2) incomplete/ admitted
        if _is_incomplete(e):
            w = 1.5
            gaps.append(DriftGap(
                name=name,
                reason="incomplete_proof",
                weight=w,
                hints=["Finish the proof or attach lemma reuse suggestions."]
            ))
            total += w
        # 3) empty logic
        if not (e.get("logic") or e.get("logic_raw") or e.get("codexlang",{}).get("logic")):
            w = 1.0
            gaps.append(DriftGap(
                name=name,
                reason="empty_logic",
                weight=w,
                hints=["Provide logic or remove placeholder node."]
            ))
            total += w

    status = DriftStatus.CLOSED if total == 0 else (DriftStatus.DRIFTING if total > 2 else DriftStatus.OPEN)

    return DriftReport(
        container_id=container.get("id"),
        total_weight=round(total, 3),
        status=status,
        gaps=gaps,
        meta={"count": len(entries)}
    )