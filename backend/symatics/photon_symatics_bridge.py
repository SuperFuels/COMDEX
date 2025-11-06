# =========================================================
# 📁 backend/symatics/photon_symatics_bridge.py
# =========================================================
"""
⚛ Photon-Symatics Bridge - SRK-15
Accepts JSONL (one JSON object per line) or free text lines.
Each item is coerced into a dict like {"operator": "⊕", "args":[...]} or {"expr":"..."}.
Photonic ops (⊕, ↔, ⟲, ∇, μ) are executed in Photon runtime; others route to Symatics.
"""

from __future__ import annotations
import json
import re
from typing import Any, Dict, List, Optional

from backend.modules.photon.photon_algebra_runtime import PhotonAlgebraRuntime
from backend.symatics.operators import OPS

# ────────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────────

OP_SYMBOL_TO_NAME = {
    "⊕": "superpose",
    "↔": "entangle",
    "⟲": "resonate",
    "∇": "collapse",
    "μ": "measure",
}
PHOTON_OPS = set(OP_SYMBOL_TO_NAME.keys())

def op_color(op_symbol: str) -> str:
    return {
        "⊕": "#06B6D4",  # cyan
        "↔": "#D946EF",  # fuchsia
        "⟲": "#EAB308",  # yellow
        "∇": "#EF4444",  # red
        "μ": "#FFFFFF",  # white
    }.get(op_symbol, "#8B5CF6")  # indigo fallback


class _SymaticOperatorProxy:
    """Adapter exposing Symatics OPS via .apply()."""
    def __init__(self, ops_dict: Dict[str, Any]):
        self.ops = ops_dict

    def apply(self, op_symbol: str, *args, **kwargs):
        op = self.ops.get(op_symbol)
        if not op:
            raise ValueError(f"Unknown symbolic operator: {op_symbol}")
        if hasattr(op, "impl"):
            return op.impl(*args, **kwargs)
        if callable(op):
            return op(*args, **kwargs)
        raise TypeError(f"Operator {op_symbol} is not callable")


# ────────────────────────────────────────────────────────────────
# Coercion
# ────────────────────────────────────────────────────────────────

EMIT_RX = re.compile(r'^emit\s+["\'](.+?)["\']\s*$')

def _coerce_line_to_item(line: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort coercion:
      - JSON → dict or {"expr": ...}
      - bare op token (⊕/↔/⟲/∇/μ) → {"operator": "<sym>"}
      - emit "x" → {"operator":"emit","args":["x"]}
      - otherwise → {"expr": "<line>"}
    """
    s = (line or "").strip()
    if not s:
        return None
    # JSON line?
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return obj
        if isinstance(obj, str):
            return {"expr": obj}
        return {"expr": obj}
    except Exception:
        pass

    if s in PHOTON_OPS:
        return {"operator": s}
    m = EMIT_RX.match(s)
    if m:
        return {"operator": "emit", "args": [m.group(1)]}
    return {"expr": s}


def _build_capsule_from_item(it: Dict[str, Any]) -> Dict[str, Any]:
    """
    Minimal Photon capsule. Ensures glyph entry is a dict (never a raw string).
    """
    glyph = {}
    if "operator" in it:
        glyph["operator"] = it["operator"]
        if "args" in it:
            glyph["args"] = it["args"]
        if "meta" in it:
            glyph["meta"] = it["meta"]
    elif "expr" in it:
        # non-operator line: keep as expr; runtime may skip
        glyph["expr"] = it["expr"]
    else:
        # unknown shape → wrap
        glyph["expr"] = it

    return {
        "name": "bridge_inline",
        "glyphs": [glyph],
    }


# ────────────────────────────────────────────────────────────────
# Bridge
# ────────────────────────────────────────────────────────────────

class PhotonSymaticsBridge:
    """
    Routes photonic ops to Photon runtime; other ops to Symatics.
    Produces UI-friendly traces (color, op, result).
    """

    def __init__(self):
        self.photon_runtime = PhotonAlgebraRuntime()
        self.sym_proxy = _SymaticOperatorProxy(OPS)

    def resolve_operator_domain(self, op_symbol: str) -> str:
        return "photon" if op_symbol in PHOTON_OPS else "symatic"

    async def execute_raw(self, source_text: str) -> Dict[str, Any]:
        """
        Accepts JSONL or free text. Coerces each line to an item dict,
        then executes per domain. Non-operator expr lines are skipped.
        """
        lines = (source_text or "").splitlines()
        items: List[Dict[str, Any]] = []
        for ln in lines:
            obj = _coerce_line_to_item(ln)
            if obj is not None:
                items.append(obj)

        results: List[Dict[str, Any]] = []
        for it in items:
            # For the response, keep the original item visible as JSON (matches your previous output)
            shown_input = json.dumps(it, ensure_ascii=False)

            op = it.get("operator")
            if not op:
                # Pure expr → no operator to handle
                results.append({
                    "input": it.get("expr") if "expr" in it else shown_input,
                    "status": "skipped",
                    "note": "no supported operator found",
                })
                continue

            # Dispatch by domain
            domain = self.resolve_operator_domain(op)
            if domain == "photon":
                try:
                    cap = _build_capsule_from_item(it)   # glyph is a dict
                    exec_result = await self.photon_runtime.execute(cap)
                    results.append({
                        "input": shown_input,
                        "op": op,
                        "color": op_color(op),
                        "status": "ok",
                        "result": exec_result,
                    })
                except Exception as e:
                    results.append({
                        "input": shown_input,
                        "op": op,
                        "color": "#DC2626",
                        "status": "error",
                        "error": str(e),
                    })
            else:
                # Symatic fallback (e.g., "emit") – try to run, otherwise mark skipped
                try:
                    args = it.get("args", []) or []
                    self.sym_proxy.apply(op, *args)
                    results.append({
                        "input": shown_input,
                        "op": op,
                        "color": op_color(op),
                        "status": "ok",
                    })
                except Exception as e:
                    results.append({
                        "input": shown_input,
                        "op": op,
                        "color": "#64748B",
                        "status": "skipped",
                        "note": f"symatic op not handled: {e}",
                    })

        return {"ok": True, "count": len(results), "results": results}