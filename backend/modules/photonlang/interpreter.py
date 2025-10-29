from __future__ import annotations
from typing import Any, Dict, Tuple, List
from dataclasses import dataclass

# Pull in real Symatics dispatch if available
try:
    from backend.symatics.symatics_dispatcher import evaluate_symatics_expr
except Exception:
    def evaluate_symatics_expr(spec: Dict[str, Any]) -> Dict[str, Any]:
        op = spec.get("op"); args = spec.get("args", [])
        return {"op": op, "args": args, "result": f"{' '.join(map(str,args))} {op}"}

# Stubs/adapters that map to your real modules when present
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
    id: str; mode: str = "symbolic"
    def seed(self, pattern: str, coherence: float = 1.0):
        return {"seeded": pattern, "coherence": coherence}

class QuantumFieldCanvas:
    def __init__(self, dim: int = 2): self.dim = dim; self.state = {}
    def inject(self, sheet: AtomSheet): self.state["sheet"] = sheet; return {"injected": True}
    def resonate(self, seq: str, intensity: float = 1.0):
        # interpret glyph seq via Symatics for realism
        results = []
        for ch in seq:
            if ch in "⊕↔⟲μπ⇒∇":
                results.append(evaluate_symatics_expr({"op": ch, "args": []}))
        self.state["resonance"] = {"seq": seq, "intensity": intensity, "ops": results}
        return self.state["resonance"]

# Wormhole transport (no-op stub unless a transport is wired)
def send_through_wormhole(obj: Any, uri: str) -> Dict[str, Any]:
    return {"sent": True, "uri": uri, "payload": str(obj)}

# Save .ptn (serialize minimal doc)
def save_as_ptn(target: str, env: Dict[str, Any]) -> Dict[str, Any]:
    import json, os
    if not target.endswith(".ptn"):
        target += ".ptn"
    os.makedirs("artifacts", exist_ok=True)
    path = f"artifacts/{os.path.basename(target)}"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"env": list(env.keys())}, f, indent=2, ensure_ascii=False)
    return {"saved": path}

# ---------- Execution ----------
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
        obj = eval_expr(node.obj, env); return getattr(obj, node.name)
    if isinstance(node, Call):
        func = eval_expr(node.func, env)
        args = []; kwargs = {}
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
            # bind names as placeholders; real module hook-in upstream
            for n in s.names: env[n] = env.get(n, object())
        elif isinstance(s, FromImport):
            for n in s.names: env[n] = env.get(n, object())
        elif isinstance(s, WormholeImport):
            # import a “class” stub from a wormhole URI
            # here we expose the name with a constructor capturing the URI
            name = s.name
            def _factory(*args, **kwargs): return {"wormhole": s.uri, "args": args, "kwargs": kwargs}
            env[name] = _factory
        elif isinstance(s, GlyphInit):
            # initialize symbolic-quantum interface by “touching” glyphs
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
            target = eval_expr(s.target, env) if hasattr(s.target, "value")==False else s.target.value
            last = save_as_ptn(str(target), env)
        else:
            # call_stmt or raw expr
            last = eval_expr(s, env)

    return {
        "status": "success",
        "glyph_boot": glyph_boot_done,
        "last": last,
        "env_keys": sorted(env.keys()),
    }

def run_source(source: str, **kwargs):
    return execute(parse_source(source), **kwargs)