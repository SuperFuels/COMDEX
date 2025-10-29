from __future__ import annotations
from typing import Any, Dict, Tuple, List
from dataclasses import dataclass
import asyncio

# ============================================================
# 🔹 Symatics Dispatch Layer
# ============================================================
try:
    from backend.symatics.symatics_dispatcher import evaluate_symatics_expr
except Exception:
    def evaluate_symatics_expr(spec: Dict[str, Any]) -> Dict[str, Any]:
        op = spec.get("op"); args = spec.get("args", [])
        return {"op": op, "args": args, "result": f"{' '.join(map(str,args))} {op}"}


# --- Photon SQI Resonance Bridge (optional) ---------------------------------
try:
    from backend.modules.photonlang.integrations.photon_sqi_resonance_bridge import BRIDGE as PHOTON_SQI_BRIDGE
except Exception:
    class _StubBridge:
        async def integrate_all(self, state, container_id=None):
            print(f"[StubBridge] Skipping resonance integration for {state.get('seq')}")
    PHOTON_SQI_BRIDGE = _StubBridge()
# ----------------------------------------------------------------------------


# ============================================================
# 🔹 Stubs / Adapters
# ============================================================
class SQI:
    @staticmethod
    def monitor(obj): return SQI
    @staticmethod
    def optimize(): return {"sqi_optimized": True}

class GHX:
    @staticmethod
    def render(obj): return {"rendered": True}

@dataclass
class AtomSheet:
    id: str
    mode: str = "symbolic"
    def seed(self, pattern: str, coherence: float = 1.0):
        return {"seeded": pattern, "coherence": coherence}

class QuantumFieldCanvas:
    def __init__(self, dim: int = 2):
        self.dim = dim
        self.state = {}

    def inject(self, sheet: AtomSheet):
        self.state["sheet"] = sheet
        return {"injected": True}

    async def resonate(self, seq: str, intensity: float = 1.0, container_id: str | None = None):
        """
        Interpret a symbolic sequence via Symatics, emit resonance telemetry,
        and persist the result using the Photon Telemetry Recorder.
        """
        results = []
        for ch in seq:
            if ch in "⊕↔⟲μπ⇒∇":
                results.append(evaluate_symatics_expr({"op": ch, "args": []}))

        self.state["resonance"] = {
            "seq": seq,
            "intensity": intensity,
            "ops": results,
        }

        # --- SQI + QQC Integration ---
        try:
            await PHOTON_SQI_BRIDGE.integrate_all(self.state, container_id)
        except Exception as e:
            print(f"[QFC::Resonate] ⚠️ SQI bridge failed: {e}")

        # --- Telemetry Recording ---
        try:
            from backend.modules.photonlang.integrations.photon_telemetry_recorder import RECORDER
            RECORDER.record_event(self.state, container_id=container_id, label="photon_resonance")
        except Exception as e:
            print(f"[QFC::Resonate] ⚠️ Telemetry recording failed: {e}")

        return self.state["resonance"]

# ============================================================
# 🔹 Wormhole Bridge — Integrated with Real Teleport Manager
# ============================================================
from backend.modules.teleport.wormhole_manager import WormholeManager

WORMHOLE = WormholeManager()

def send_through_wormhole(obj: Any, uri: str) -> Dict[str, Any]:
    """
    Bridge PhotonLang 'send ... through wormhole' syntax to WormholeManager.
    Supports URIs like 'glyphnet://aion-reflection' or 'wormhole://ucs_hub'.
    """
    try:
        dst = uri.split("://")[-1].replace("-", "_")
        result = WORMHOLE.transfer_state({"payload": str(obj)}, dst)
        return {"status": "ok", "uri": uri, "result": result}
    except Exception as e:
        return {"status": "error", "uri": uri, "error": str(e)}


# ============================================================
# 🔹 Save as .ptn
# ============================================================
def save_as_ptn(target: str, env: Dict[str, Any]) -> Dict[str, Any]:
    import json, os
    if not target.endswith(".ptn"):
        target += ".ptn"
    os.makedirs("artifacts", exist_ok=True)
    path = f"artifacts/{os.path.basename(target)}"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"env": list(env.keys())}, f, indent=2, ensure_ascii=False)
    return {"saved": path}


# ============================================================
# 🔹 Execution Core
# ============================================================
from .parser import (
    Program, ImportStmt, FromImport, WormholeImport, GlyphInit,
    Assign, Call, Attr, Name, Literal, SendThrough, SaveAs, parse_source
)

BUILTINS = {
    "SQI": SQI,
    "GHX": GHX,
    "AtomSheet": AtomSheet,
    "QuantumFieldCanvas": QuantumFieldCanvas,
}

def eval_expr(node, env):
    if isinstance(node, Name):
        return env[node.id]
    if isinstance(node, Literal):
        return node.value
    if isinstance(node, Attr):
        obj = eval_expr(node.obj, env)
        return getattr(obj, node.name)
    if isinstance(node, Call):
        func = eval_expr(node.func, env)
        args = []
        kwargs = {}
        for k, v in node.args:
            if k:
                kwargs[k] = eval_expr(v, env)
            else:
                args.append(eval_expr(v, env))
        return func(*args, **kwargs)
    raise TypeError(f"Unsupported expr: {type(node)}")

def execute(program: Program, *, initial_env: Dict[str, Any] | None = None) -> Dict[str, Any]:
    env: Dict[str, Any] = dict(BUILTINS)
    if initial_env:
        env.update(initial_env)
    last = None
    glyph_boot_done = False

    for s in program.stmts:
        if isinstance(s, ImportStmt):
            for n in s.names:
                env[n] = env.get(n, object())

        elif isinstance(s, FromImport):
            for n in s.names:
                env[n] = env.get(n, object())

        elif isinstance(s, WormholeImport):
            name = s.name
            uri = s.uri

            class WormholeProxy:
                def __init__(self, *args, **kwargs):
                    self.wormhole_uri = uri
                    self.args = args
                    self.kwargs = kwargs
                def __repr__(self):
                    return f"<WormholeProxy {name} -> {uri}>"
                def __getattr__(self, item):
                    def _stub(*args, **kwargs):
                        return {"wormhole_call": item, "args": args, "kwargs": kwargs, "uri": self.wormhole_uri}
                    return _stub
            env[name] = WormholeProxy

        elif isinstance(s, GlyphInit):
            for ch in s.seq:
                if ch in "⊕↔⟲μπ⇒∇":
                    evaluate_symatics_expr({"op": ch, "args": []})
            glyph_boot_done = True

        elif isinstance(s, Assign):
            env[s.name] = eval_expr(s.expr, env)
            last = env[s.name]

        elif isinstance(s, SendThrough):
            payload = eval_expr(s.obj, env)
            last = send_through_wormhole(payload, s.uri)

        elif isinstance(s, SaveAs):
            target = eval_expr(s.target, env) if not hasattr(s.target, "value") else s.target.value
            last = save_as_ptn(str(target), env)

        else:
            last = eval_expr(s, env)

    return {
        "status": "success",
        "glyph_boot": glyph_boot_done,
        "last": last,
        "env_keys": sorted(env.keys()),
    }

def run_source(source: str, **kwargs):
    return execute(parse_source(source), **kwargs)