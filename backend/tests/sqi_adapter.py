# backend/tests/sqi_adapter.py
import time
import uuid
from typing import Any, Dict, Union
from collections.abc import Mapping
import logging

from backend.modules.tessaris.thought_branch import (
    ThoughtBranch,
    execute_branch_from_glyph,
    BranchNode,
)
from backend.modules.sqi.sqi_tessaris_bridge import SQITessarisBridge

log = logging.getLogger(__name__)

# -------- Hashable wrapper to avoid "unhashable dict" anywhere ----------
class HashableDict(Mapping):
    __slots__ = ("_d", "_h")
    def __init__(self, data: dict):
        if not isinstance(data, dict):
            raise TypeError("HashableDict expects a dict")
        self._d = data
        oid = data.get("origin_id") or data.get("id") or data.get("label") or id(self)
        self._h = hash(str(oid))

    def __getitem__(self, k): return self._d[k]
    def __iter__(self): return iter(self._d)
    def __len__(self): return len(self._d)
    def __getattr__(self, name):
        try: return self._d[name]
        except KeyError as e: raise AttributeError(name) from e
    def __hash__(self): return self._h


# -------- Normalizers / coercers ---------------------------------------
def _normalize_glyph(d: dict) -> dict:
    if "id" not in d:
        d = {**d, "id": d.get("origin_id") or d.get("label") or f"glyph_{uuid.uuid4()}"}
    if "origin_id" not in d:
        d = {**d, "origin_id": d["id"]}
    if "kind" in d and "type" not in d:
        d = {**d, "type": d["kind"]}
    return d

def glyph_to_symbol_str(g: Any) -> str:
    """
    Ensure we always hand Tessaris a *string* symbol (e.g. 'THINK').
    Looks in common places for a string; falls back to 'THINK'.
    """
    if isinstance(g, str):
        return g
    if isinstance(g, Mapping):
        # obvious symbol fields
        for key in ("symbol", "logic", "value", "label", "text"):
            v = g.get(key)
            if isinstance(v, str) and v.strip():
                return v
        # payload often carries the logic string
        p = g.get("payload")
        if isinstance(p, Mapping):
            for key in ("logic", "text", "value"):
                v = p.get(key)
                if isinstance(v, str) and v.strip():
                    return v
    return "THINK"

def coerce_thought_glyph_from_lean(lean_like: dict) -> dict:
    """
    Canonical Tessaris glyph schema:
      {
        id, origin_id,
        symbol: <STRING>,     # IMPORTANT: must be a string (e.g. "THINK")
        payload: {...}        # arbitrary info, e.g. logic string
      }
    """
    lean_like = _normalize_glyph(lean_like or {})
    logic_str = (
        lean_like.get("logic")
        or lean_like.get("value")
        or lean_like.get("text")
        or lean_like.get("expr")
        or "(unknown)"
    )
    return {
        "id": lean_like["id"],
        "origin_id": lean_like["origin_id"],
        "symbol": "THINK",               # ← keep this a STRING for ThoughtBranch
        "payload": {"logic": logic_str, "source": "lean"},
    }

def to_hashabledict(obj):
    if isinstance(obj, HashableDict): return obj
    if isinstance(obj, dict):  return HashableDict({k: to_hashabledict(v) for k, v in obj.items()})
    if isinstance(obj, list):  return [to_hashabledict(v) for v in obj]
    if isinstance(obj, tuple): return tuple(to_hashabledict(v) for v in obj)
    if isinstance(obj, set):   return {to_hashabledict(v) for v in obj}
    return obj

def wrap_glyphs_inplace(obj):
    """Ensure any nested ...['glyph'] dicts are hashable."""
    if isinstance(obj, dict):
        if "glyph" in obj and isinstance(obj["glyph"], dict):
            obj["glyph"] = HashableDict(_normalize_glyph(obj["glyph"]))
        for v in obj.values():
            wrap_glyphs_inplace(v)
    elif isinstance(obj, list):
        for v in obj:
            wrap_glyphs_inplace(v)


# -------- Tessaris + SQI runners (contracted) --------------------------
def run_tessaris_branch(engine, glyph_dict: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a ThoughtBranch from a canonical glyph and execute it.

    IMPORTANT: execute_branch_from_glyph in our tree expects a *string* glyph.
    We coerce to a plain symbol here and then convert the resulting dict back
    to a ThoughtBranch instance.
    """
    glyph_str = glyph_to_symbol_str(glyph_dict)
    br = execute_branch_from_glyph(glyph_str, context or {})
    br_dict = br["branch"]
    br_dict["origin_id"] = br_dict.get("origin_id", str(uuid.uuid4()))
    branch = ThoughtBranch.from_dict(br_dict)

    # Some engine builds expect position to be a dict (not an int)
    if not isinstance(getattr(branch, "position", None), dict):
        try:
            step = int(getattr(branch, "position", 0) or 0)
        except Exception:
            step = 0
        branch.position = {"coord": [0, 0, 0], "step": step}

    # Execute and time
    t0 = time.time()
    try:
        engine.execute_branch(branch)
        t1 = time.time()
        return {"branch": branch, "exec_time": max(t1 - t0, 1e-6)}
    except Exception:
        logging.exception("Baseline Tessaris execution failed")
        return {"branch": branch, "exec_time": float("inf")}

def run_sqi(engine, glyph_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate & collapse q-branches with the SQI bridge.
    Payloads in/out are made hashable to avoid set/dict key crashes downstream.

    If the engine lacks expand_thought_branch, we provide a tiny fallback that
    uses BranchNode.generate_branches() based on the glyph symbol.
    """
    # Provide a minimal expand function if the engine doesn't have one
    if not hasattr(engine, "expand_thought_branch"):
        def _expand_thought_branch(root_thought: Union[str, Mapping]):
            # Accept either {"glyph": ...} or a raw symbol
            g = root_thought.get("glyph") if isinstance(root_thought, Mapping) else root_thought
            sym = glyph_to_symbol_str(g)
            root = BranchNode(symbol=sym)
            # Build small dict objects the bridge can consume
            children = []
            for c in root.generate_branches():
                child_gl = {"id": f"glyph_{uuid.uuid4()}",
                            "origin_id": f"glyph_{uuid.uuid4()}",
                            "symbol": c.symbol,
                            "payload": {"source": "expand"}}
                children.append({"glyph": child_gl})
            return children
        engine.expand_thought_branch = _expand_thought_branch  # type: ignore

    # Bridge with hashable I/O wrapping
    bridge = SQITessarisBridge(engine)
    gen0 = bridge.generate_q_thought_branches
    col0 = bridge.collapse_qpath
    bridge.generate_q_thought_branches = lambda p: to_hashabledict(gen0(to_hashabledict(p)))
    bridge.collapse_qpath = lambda qb, *a, **k: to_hashabledict(col0(to_hashabledict(qb), *a, **k))

    # Kick it off
    payload = {"glyph": to_hashabledict(_normalize_glyph(glyph_dict))}
    t0 = time.time()
    try:
        q_branches = bridge.generate_q_thought_branches(payload)
        wrap_glyphs_inplace(q_branches)  # ensure hashable glyphs in nested results
        resolved = [bridge.collapse_qpath(qb, bias="logic") for qb in q_branches]
        t1 = time.time()
        return {"q_branches": q_branches, "resolved": resolved, "exec_time": max(t1 - t0, 1e-5)}
    except Exception:
        logging.exception("SQI execution failed")
        return {"q_branches": [], "resolved": [], "exec_time": float("inf")}