# backend/modules/sqi/sqi_tessaris_bridge.py

from typing import Dict, Any, List, Optional, Tuple

# Use the active singleton/instance exposed by UCS
from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime

# ---------- Helpers ----------

def _as_list(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, (list, tuple, set)):
        return [str(x) for x in v]
    return [str(v)]

def _as_set(x: Any) -> set:
    if not x:
        return set()
    if isinstance(x, (list, tuple, set)):
        return set(x)
    return {x}

def _normalize_goal(goal: Dict[str, Any]) -> Dict[str, Any]:
    # keep id/address as-is; normalize caps/tags/nodes to lists of strings
    return {
        "id": goal.get("id"),
        "address": (goal.get("address") or "").strip(),
        "caps": _as_list(goal.get("caps")),
        "tags": _as_list(goal.get("tags")),
        "nodes": _as_list(goal.get("nodes")),
    }

def _normalize_atom_entry(entry: Any) -> Tuple[Optional[str], Dict[str, Any], Dict[str, Any]]:
    """
    Normalize ucs_runtime.atom_index values into:
      (container_name, atom_obj, raw_entry_dict)
    Supports tuple-style (container, obj) and dict-style entries.
    """
    if isinstance(entry, tuple) and len(entry) == 2:
        container_name, atom_obj = entry
        return container_name, (atom_obj or {}), {"container": container_name, "ref": atom_obj}
    if isinstance(entry, dict):
        container_name = entry.get("container") or entry.get("container_id")
        atom_obj = entry.get("ref") or entry.get("atom") or entry
        return container_name, (atom_obj or {}), entry
    return None, {}, {}

def _extract_meta(atom_id: str,
                  container_name: Optional[str],
                  atom_obj: Dict[str, Any],
                  raw_entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Be generous: try meta on the atom entry; if missing, try the referenced container.
    Finally, try a container whose id == atom_id.
    """
    # 1) meta on the atom object or raw entry
    meta = (atom_obj.get("meta") or raw_entry.get("meta") or {})
    if meta:
        return meta

    # 2) meta on the referenced container
    try:
        if container_name and hasattr(ucs_runtime, "get_container"):
            cont = ucs_runtime.get_container(container_name)
            if isinstance(cont, dict):
                m = cont.get("meta") or {}
                if m:
                    return m
    except Exception:
        pass

    # 3) meta on container named by atom_id
    try:
        if hasattr(ucs_runtime, "get_container"):
            cont = ucs_runtime.get_container(atom_id)
            if isinstance(cont, dict):
                m = cont.get("meta") or {}
                if m:
                    return m
    except Exception:
        pass

    return {}

def _match(goal: Dict[str, Any], meta: Dict[str, Any]) -> bool:
    # Address direct match override inside fallback
    g_addr = (goal.get("address") or "").strip()
    m_addr = (meta or {}).get("address") or ""
    if g_addr and g_addr == m_addr:
        return True

    # Subset match for caps/tags/nodes
    g_caps  = _as_set(goal.get("caps"))
    g_tags  = _as_set(goal.get("tags"))
    g_nodes = _as_set(goal.get("nodes"))

    m_caps  = _as_set((meta or {}).get("caps"))
    m_tags  = _as_set((meta or {}).get("tags"))
    m_nodes = _as_set((meta or {}).get("nodes"))

    if g_caps  and not g_caps.issubset(m_caps):   return False
    if g_tags  and not g_tags.issubset(m_tags):   return False
    if g_nodes and not g_nodes.issubset(m_nodes): return False
    return True

def _score(goal: Dict[str, Any], meta: Dict[str, Any]) -> float:
    g_caps  = _as_set(goal.get("caps"))
    g_tags  = _as_set(goal.get("tags"))
    g_nodes = _as_set(goal.get("nodes"))

    m_caps  = _as_set((meta or {}).get("caps"))
    m_tags  = _as_set((meta or {}).get("tags"))
    m_nodes = _as_set((meta or {}).get("nodes"))

    score = 0.0
    # weight nodes higher to reflect structural intent, then caps, then tags
    if g_nodes: score += 1.5 * len(g_nodes.intersection(m_nodes))
    if g_caps:  score += 1.0 * len(g_caps.intersection(m_caps))
    if g_tags:  score += 0.5 * len(g_tags.intersection(m_tags))
    return score

def _fallback_choose_route(goal: Dict[str, Any], k: int = 3) -> List[str]:
    matches: List[Tuple[str, float]] = []
    atom_index = getattr(ucs_runtime, "atom_index", {}) or {}

    for atom_id, entry in atom_index.items():
        container_name, atom_obj, raw_entry = _normalize_atom_entry(entry)
        meta = _extract_meta(atom_id, container_name, atom_obj, raw_entry)
        if _match(goal, meta):
            matches.append((atom_id, _score(goal, meta)))

    matches.sort(key=lambda t: t[1], reverse=True)
    return [a for a, _ in matches[:k]]

# ---------- Public API ----------

def choose_route(goal: Dict[str, Any], k: int = 3) -> Dict[str, Any]:
    """
    Entry used by ucs_paths.py.
    Resolution order:
       1) Address override (goal.address → resolve_atom)
       2) Runtime compose_path (uses UCSRuntime.atom_index scoring)
       3) Metadata fallback (subset match w/ scoring on caps/nodes/tags)
    """
    norm_goal = _normalize_goal(goal)

    # 1) Address override
    g_addr = norm_goal.get("address") or ""
    if g_addr:
        try:
            atom_id = None
            if hasattr(ucs_runtime, "resolve_atom"):
                atom_id = ucs_runtime.resolve_atom(g_addr)
            atom_ids = [atom_id] if atom_id else []
        except Exception:
            atom_ids = []
    else:
        # 2) Preferred: UCS runtime compose_path
        atom_ids: List[str] = []
        try:
            if hasattr(ucs_runtime, "compose_path"):
                atom_ids = list(ucs_runtime.compose_path(norm_goal, k=k) or [])
        except Exception:
            atom_ids = []

        # 3) Fallback: metadata scorer
        if not atom_ids:
            atom_ids = _fallback_choose_route(norm_goal, k=k)

    return {
        "goal_id": norm_goal.get("id"),
        "goal": norm_goal,
        "atoms": atom_ids,
        "plan": [{"atom_id": a, "mode": "sequential"} for a in atom_ids],
    }

def execute_route(plan: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lightweight executor stub: walks the plan and reports per-step status.
    If your runtime has an executor, you can delegate here instead.
    """
    out: Dict[str, Any] = {"steps": [], "ok": True}
    atom_index = getattr(ucs_runtime, "atom_index", {}) or {}

    for step in plan.get("plan", []):
        atom_id = step.get("atom_id")
        tup = atom_index.get(atom_id)

        if not tup:
            out["steps"].append({"atom_id": atom_id, "status": "missing"})
            out["ok"] = False
            continue

        container_name: Optional[str] = None
        atom_obj: Any = None
        if isinstance(tup, tuple) and len(tup) == 2:
            container_name, atom_obj = tup
        elif isinstance(tup, dict):
            container_name = tup.get("container") or tup.get("container_id")
            atom_obj = tup.get("ref") or tup.get("atom") or tup

        try:
            # placeholder: adapt to your actual execution behavior
            produced = {"kg_links": [], "produces": {}}
            out["steps"].append(
                {"atom_id": atom_id, "container": container_name, "status": "ok", "produced": produced}
            )
        except Exception as e:
            out["ok"] = False
            out["steps"].append(
                {"atom_id": atom_id, "container": container_name, "status": "error", "error": str(e)}
            )

    return out

# ── Existing SQI ↔ Tessaris bridge (left intact) ─────────────────────────────

from backend.modules.tessaris.tessaris_engine import TessarisEngine
from backend.modules.sqi.entangler_engine import EntanglerEngine
from backend.modules.sqi.glyph_collapse_trigger import GlyphCollapseTrigger

class SQITessarisBridge:
    def __init__(self, tessaris_engine: TessarisEngine):
        self.tessaris = tessaris_engine
        self.entangler = EntanglerEngine()
        self.collapser = GlyphCollapseTrigger()

    def generate_q_thought_branches(self, root_thought: Dict) -> List[Dict]:
        base_branches = self.tessaris.expand_thought_branch(root_thought)
        entangled = []
        for branch in base_branches:
            qglyphs = self.entangler.entangle(branch)
            entangled.append({"original": branch, "qglyphs": qglyphs})
        return entangled

    def collapse_qpath(self, qpath: Dict, bias: Optional[str] = None) -> Dict:
        resolved: Dict[str, Any] = {}
        for key, qglyph in qpath["qglyphs"].items():
            resolved[key] = self.collapser.collapse_qglyph(qglyph, observer_context=None, bias_preference=bias)
        return resolved

    def execute_superposed_reasoning(self, root_thought: Dict, bias: Optional[str] = None) -> List[Dict]:
        branches = self.generate_q_thought_branches(root_thought)
        resolved_branches = []
        for qpath in branches:
            resolved = self.collapse_qpath(qpath, bias=bias)
            resolved_branches.append(resolved)
        return resolved_branches