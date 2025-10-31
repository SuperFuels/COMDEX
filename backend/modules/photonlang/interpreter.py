from __future__ import annotations
from typing import Any, Dict, Tuple, List
from dataclasses import dataclass
import asyncio
from backend.modules.photonlang.photon_page_validator import validate_page_entanglement
# ============================================================
# 🔹 Symatics Dispatch Layer
# ============================================================
try:
    from backend.symatics.symatics_dispatcher import evaluate_symatics_expr
except Exception:
    def evaluate_symatics_expr(spec: Dict[str, Any]) -> Dict[str, Any]:
        op = spec.get("op"); args = spec.get("args", [])
        return {"op": op, "args": args, "result": f"{' '.join(map(str,args))} {op}"}

try:
    from backend.modules.photonlang.pgc import compile_photon, is_pure_glyph_program
except:
    compile_photon = lambda s: None
    is_pure_glyph_program = lambda s: False

# ============================================================
# 🔹 Photon Grammar Compiler
# ============================================================
try:
    from backend.modules.photonlang.pgc import compile_photon as photon_compile
except Exception:
    from .parser import parse_source as photon_compile

# ============================================================
# 🔹 Photon Modulation Hook (⧖)
# ============================================================
try:
    from backend.modules.photonlang.operators.parametric_ops import modulate as photon_modulate
except Exception:
    def photon_modulate(wave, params):
        wave = dict(wave)
        wave["frequency"] = wave.get("frequency", 1) * params.get("freq", 1)
        wave["amplitude"] = wave.get("amplitude", 1) * params.get("amp", 1)
        return wave

# ============================================================
# 🔹 Photon SQI Resonance Bridge (optional)
# ============================================================
try:
    from backend.modules.photonlang.integrations.photon_sqi_resonance_bridge import BRIDGE as PHOTON_SQI_BRIDGE
except Exception:
    class _StubBridge:
        async def integrate_all(self, state, container_id=None):
            print(f"[StubBridge] Skipping resonance integration for {state.get('seq')}")
    PHOTON_SQI_BRIDGE = _StubBridge()

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

# ============================================================
# 🔹 QuantumFieldCanvas + ⧖ integration
# ============================================================
class QuantumFieldCanvas:
    """
    Photon–Wave resonance orchestrator.
    Orchestrates symbolic → waveform → telemetry pipeline.
    """

    def __init__(self, dim: int = 2):
        self.dim = dim
        self.state = {
            "field_dim": dim,
            "coherence": 1.0,
            "entropy": 0.0,
            "resonance": None,
            "modulated": None,
            "ops": [],
        }

    def inject(self, sheet: AtomSheet):
        self.state["sheet"] = sheet
        return {"injected": True, "sheet_id": sheet.id}

    async def resonate(self, seq: str, intensity: float = 1.0, container_id: str | None = None):
        """
        Interpret symbolic stream via Symatics & apply optional modulation ⧖
        """
        ops = []
        modulate_pending = False

        # --- Parse symbolic ops ---
        for ch in seq:
            # Symatics operator dispatch
            if ch in "⊕↔⟲μπ⇒∇":
                ops.append(evaluate_symatics_expr({"op": ch, "args": []}))

            # Parametric modulation marker
            elif ch == "⧖":
                modulate_pending = True
                ops.append({"op": "⧖", "modulated": "pending"})

        # --- Core resonance state update ---
        self.state["resonance"] = {
            "seq": seq,
            "intensity": intensity,
            "ops": ops,
        }
        self.state["ops"].extend(ops)

        # --- Optional modulation pass ---
        if modulate_pending:
            try:
                wave = {"frequency": 1.0, "amplitude": 1.0}
                params = {"freq": 1.02, "amp": 1.01}  # gentle harmonic envelope lift
                self.state["modulated"] = photon_modulate(wave, params)
            except Exception as e:
                print(f"[QFC::Modulate] ⚠️ {e}")

        # --- SQI + QQC Bridge ---
        try:
            await PHOTON_SQI_BRIDGE.integrate_all(self.state, container_id)
        except Exception as e:
            print(f"[QFC::Bridge] ⚠️ {e}")

        # --- Compute inline SQI Metric ---
        self.state["sqi"] = self.state.get("coherence", 1.0) - self.state.get("entropy", 0.0)

        # --- Telemetry Recorder ---
        try:
            from backend.modules.photonlang.integrations.photon_telemetry_recorder import RECORDER
            RECORDER.record_event(self.state, container_id=container_id, label="photon_resonance")
        except Exception as e:
            print(f"[QFC::Telemetry] ⚠️ {e}")

        # --- Optional Binary Mode ---
        try:
            from backend.modules.photonlang.binary_mode import to_binary
            self.state["binary"] = to_binary(seq)
        except Exception:
            self.state["binary"] = ""

        return self.state["resonance"]

# ============================================================
# 🔹 Wormhole Bridge
# ============================================================
from backend.modules.teleport.wormhole_manager import WormholeManager
WORMHOLE = WormholeManager()

def send_through_wormhole(obj: Any, uri: str) -> Dict[str, Any]:
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
    if isinstance(node, Name): return env[node.id]
    if isinstance(node, Literal): return node.value
    if isinstance(node, Attr): return getattr(eval_expr(node.obj, env), node.name)
    if isinstance(node, Call):
        func = eval_expr(node.func, env)
        args = []
        kwargs = {}
        for k, v in node.args:
            if k: kwargs[k] = eval_expr(v, env)
            else: args.append(eval_expr(v, env))
        return func(*args, **kwargs)
    raise TypeError(f"Unsupported expr: {type(node)}")

def execute(program: Program, *, initial_env: Dict[str, Any] | None = None) -> Dict[str, Any]:
    env: Dict[str, Any] = dict(BUILTINS)
    if initial_env: env.update(initial_env)
    last = None
    glyph_boot_done = False

    for s in program.stmts:
        if isinstance(s, ImportStmt):
            for n in s.names: env[n] = env.get(n, object())

        elif isinstance(s, FromImport):
            for n in s.names: env[n] = env.get(n, object())

        elif isinstance(s, WormholeImport):
            name = s.name; uri = s.uri
            class WormholeProxy:
                def __init__(self,*a,**kw): self.wormhole_uri = uri
                def __repr__(self): return f"<WormholeProxy {name} -> {uri}>"
                def __getattr__(self,item):
                    def _stub(*args,**kw):
                        return {"wormhole_call": item, "args": args, "kwargs": kw, "uri": self.wormhole_uri}
                    return _stub
            env[name] = WormholeProxy

        elif isinstance(s, GlyphInit):
            for ch in s.seq:
                evaluate_symatics_expr({"op": ch, "args": []})
            glyph_boot_done = True

        elif isinstance(s, Assign):
            env[s.name] = eval_expr(s.expr, env); last = env[s.name]

        elif isinstance(s, SendThrough):
            payload = eval_expr(s.obj, env)
            last = send_through_wormhole(payload, s.uri)

        elif isinstance(s, SaveAs):
            target = eval_expr(s.target, env) if not hasattr(s.target,"value") else s.target.value
            last = save_as_ptn(str(target), env)

        else:
            last = eval_expr(s, env)


    # 🔹 Optional: Photon → Binary synthesis hook
    # --- Binary synthesis ---
    binary = ""

    # If glyph boot happened, encode final sequence or string
    try:
        from backend.modules.photonlang.binary_mode import to_binary

        if glyph_boot_done:
            if isinstance(last, dict) and "seq" in last:
                binary = to_binary(last["seq"])
            elif isinstance(last, str) and last.strip() and all(ch in "⊕↔⟲μπ⇒∇⧖" for ch in last.strip()):
                binary = to_binary(last.strip())

        # Final fallback for glyph-return values
        elif isinstance(last, str) and last.strip() and all(ch in "⊕↔⟲μπ⇒∇⧖" for ch in last.strip()):
            binary = to_binary(last.strip())

    except Exception:
        binary = ""

    return {
        "status": "success",
        "glyph_boot": glyph_boot_done,
        "last": last,
        "env_keys": sorted(env.keys()),
        "binary": binary or "",
    }

def run_source(source: str, **kwargs):
    src = source.strip()

    # ✅ .ptn page auto-runner
    if src.endswith(".ptn") and os.path.exists(src):
        from backend.modules.photonlang.page_runner import run_ptn_page
        return run_ptn_page(src)

    # ✅ pure glyph → compile & execute Photon program
    if is_pure_glyph_program(src):
        prog = compile_photon(src)
        if prog and prog.stmts:
            out = execute(prog, **kwargs)
        else:
            # direct glyph execution path
            out = execute(parse_source(source), **kwargs)
    else:
        # ✅ normal Photon script
        out = execute(parse_source(source), **kwargs)

    # ✅ Pure glyph? enforce binary
    glyph_chars = "⊕↔⟲μπ⇒∇⧖"
    if src and all(ch in glyph_chars for ch in src):
        out["glyph_boot"] = True
        try:
            from backend.modules.photonlang.binary_mode import to_binary
            out["binary"] = to_binary(src)
        except Exception:
            out["binary"] = ""

    # ✅ Guarantee binary exists
    if "binary" not in out:
        out["binary"] = ""

    # ✅ FINAL safety — if pure glyph and still empty binary → force encode
    if out["binary"] == "" and src and all(ch in glyph_chars for ch in src):
        out["glyph_boot"] = True
        try:
            from backend.modules.photonlang.binary_mode import to_binary
            out["binary"] = to_binary(src)
        except Exception:
            out["binary"] = ""

    return out