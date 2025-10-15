# -*- coding: utf-8 -*-
# File: backend/modules/codexcore_virtual/instruction_registry.py
"""
Instruction Registry for Virtual CodexCore

- Maps CodexLang symbolic operators to runtime handlers.
- All ops are now registered with **domain-tagged keys**
  (e.g. "logic:⊕", "control:⟲", "physics:∇").
- Backward compatibility: raw glyph lookups are redirected with a warning.
- Supports multi-argument calls, kwargs, and hot overrides.
"""

import warnings
from backend.symatics import symatics_rulebook as SR
from typing import Callable, Dict, Any, Optional

# --------------------------
# Core Instruction Registry
# --------------------------

class InstructionRegistry:
    def __init__(self):
        # Handlers take signature: handler(ctx, *args, **kwargs) -> Any
        self.registry: Dict[str, Callable[..., Any]] = {}
        self.aliases: Dict[str, str] = {}  # raw_symbol → canonical domain:key

    def register(self, key: str, handler: Callable[..., Any]):
        """Register a canonical domain-tagged instruction."""
        if key in self.registry:
            raise ValueError(f"Instruction '{key}' already registered.")
        self.registry[key] = handler

    def alias(self, raw: str, canonical: str):
        """Map a raw glyph/symbol to a canonical domain-tagged key."""
        self.aliases[raw] = canonical

    def override(self, key: str, handler: Callable[..., Any]):
        """Force override (useful for mutation/hot patching)."""
        self.registry[key] = handler

    def list_instructions(self) -> Dict[str, str]:
        return {key: func.__name__ for key, func in self.registry.items()}

    # --- Execution APIs ---

    def execute(self, key: str, operand: Any = None) -> Any:
        """
        Back-compat single-operand entrypoint.
        Resolves legacy or canonical instruction keys via alias shim.
        Executes symbolic → photonic operations with context-safety.
        """
        # --- Normalize the instruction key ---
        if key not in self.registry:
            if key in self.aliases:
                canonical = self.aliases[key]
                warnings.warn(
                    f"[compat] Raw symbol '{key}' redirected to canonical '{canonical}'",
                    DeprecationWarning
                )
                key = canonical
            else:
                warnings.warn(
                    f"[registry] Unknown instruction key: '{key}' (skipped)",
                    RuntimeWarning
                )
                return None

        fn = self.registry.get(key)
        if not callable(fn):
            raise TypeError(f"Invalid handler for instruction '{key}': not callable")

        # --- Handle dict operands (args, kwargs) ---
        if isinstance(operand, dict):
            if "args" in operand or "kwargs" in operand:
                args = operand.get("args", [])
                kwargs = operand.get("kwargs", {})
                return fn(None, *args, **kwargs)  # ctx=None for CPU core
            # flat dict → kwargs style
            return fn(None, **operand)

        # --- Handle single operand or None ---
        if operand is None:
            return fn(None)
        else:
            return fn(None, operand)

    def execute_v2(self, key: str, *args, **kwargs) -> Any:
        """
        Modern var-arg entrypoint (preferred).
        - Supports ctx and context explicitly.
        - Applies alias redirection with warnings.
        """
        if key not in self.registry:
            if key in self.aliases:
                canonical = self.aliases[key]
                warnings.warn(
                    f"[compat] Raw symbol '{key}' redirected to '{canonical}'",
                    DeprecationWarning
                )
                key = canonical
            else:
                raise KeyError(f"Unknown instruction key: {key}")

        fn = self.registry[key]

        # 🔑 Ensure ctx is always provided, default None
        ctx = kwargs.pop("ctx", None)
        context = kwargs.pop("context", None)  # optional semantic context

        # Pass both ctx and context if handler declares them
        try:
            return fn(ctx, *args, context=context, **kwargs)
        except TypeError:
            # Fallback: if handler doesn't accept `context`, retry without it
            return fn(ctx, *args, **kwargs)


# Global default registry
registry = InstructionRegistry()

# --------------------------
# Simple built-in handlers
# --------------------------

def handle_reflect(_ctx, data=None, context=None, **_kw):
    return f"[REFLECT] {data}"

def handle_store(_ctx, data=None, context=None, **_kw):
    return f"[STORE] {data}"

def handle_recall(_ctx, data=None, context=None, **_kw):
    return f"[RECALL] {data}"

def handle_sequence(_ctx, left=None, right=None, context=None, **_kw):
    return {"sequence": [left, right]}

# Register canonical + alias
registry.register("logic:→", handle_sequence)
registry.alias("→", "logic:→")

# Canonical domain-tag registrations
registry.register("control:⟲", handle_reflect)
registry.register("logic:⊕", handle_store)
registry.register("memory:↺", handle_recall)

# Backward aliases
registry.alias("⟲", "control:⟲")
registry.alias("⊕", "logic:⊕")
registry.alias("↺", "memory:↺")

# ---------------------------------
# Optional Physics Operator Handlers
# ---------------------------------

def _to_python(obj: Any) -> Any:
    if obj is None:
        return None
    to_dict = getattr(obj, "to_dict", None)
    if callable(to_dict):
        try:
            return to_dict()
        except Exception:
            pass
    return obj

try:
    from backend.modules.symbolic_engine import physics_kernel as PK
except Exception:
    PK = None

def _need_pk(name: str):
    if PK is None:
        raise RuntimeError(f"physics_kernel not available; cannot execute '{name}'.")

# Vector calculus
def _h_grad(ctx, field=None, coords=None, context=None, **kw):      # ∇
    _need_pk("∇")
    return _to_python(PK.grad(field, coords))

def _h_div(ctx, vec=None, coords=None, context=None, **kw):        # ∇·
    _need_pk("∇·")
    return _to_python(PK.div(vec, coords))

def _h_curl(ctx, vec=None, coords=None, context=None, **kw):       # ∇×
    _need_pk("∇×")
    return _to_python(PK.curl(vec, coords))

def _h_laplacian(ctx, field=None, coords=None, context=None, **kw):  # Δ
    _need_pk("Δ")
    return _to_python(PK.laplacian(field, coords))

def _h_d_dt(ctx, expr=None, t: Optional[str] = None, context=None, **kw):  # d/dt
    _need_pk("d/dt")
    return _to_python(PK.d_dt(expr, t or "t"))

# Linear algebra / tensor ops
def _h_dot(ctx, A=None, B=None, context=None, **kw):               # •
    _need_pk("•")
    return _to_python(PK.dot(A, B))

def _h_cross(ctx, A=None, B=None, context=None, **kw):             # ×
    _need_pk("×")
    return _to_python(PK.cross(A, B))

def _h_tensor(ctx, A=None, B=None, context=None, **kw):            # ⊗
    _need_pk("⊗")
    return _to_python(PK.tensor_product(A, B))

# Quantum / wave ops
def _h_hbar(ctx, context=None, **kw):                               # ℏ
    _need_pk("ℏ")
    if hasattr(PK, "hbar"):
        return _to_python(PK.hbar())
    raise NotImplementedError

def _h_schrod(ctx, psi=None, H=None, t: Optional[str] = None, context=None, **kw):  # iħ∂/∂t
    _need_pk("iħ∂/∂t")
    if hasattr(PK, "schrodinger"):
        return _to_python(PK.schrodinger(psi, H, t or "t"))
    raise NotImplementedError

def _h_box(ctx, field=None, coords=None, metric=None, context=None, **kw):  # □
    _need_pk("□")
    if hasattr(PK, "dalembertian"):
        return _to_python(PK.dalembertian(field, coords=coords, metric=metric))
    raise NotImplementedError

def _h_partial_mu(ctx, field=None, mu=None, coords=None, context=None, **kw):  # ∂_μ
    _need_pk("∂_μ")
    if hasattr(PK, "partial_mu"):
        return _to_python(PK.partial_mu(field, mu=mu, coords=coords))
    raise NotImplementedError

def _h_nabla_mu(ctx, field=None, mu=None, metric=None, connection=None, context=None, **kw):  # ∇_μ
    _need_pk("∇_μ")
    if hasattr(PK, "nabla_mu"):
        return _to_python(PK.nabla_mu(field, mu=mu, metric=metric, connection=connection))
    raise NotImplementedError

# ---------------------------------
# Symatics Operator Handlers
# ---------------------------------

def _h_superpose(ctx, a=None, b=None, context=None, **kw):  # ⊕
    return SR.op_superpose(a, b, context or {})

def _h_measure(ctx, expr=None, context=None, **kw):         # μ
    collapsed = SR.collapse_rule(expr)
    return SR.op_measure(collapsed, context or {})

def _h_entangle(ctx, a=None, b=None, context=None, **kw):   # ↔
    return SR.op_entangle(a, b, context or {})

def _h_recurse(ctx, expr=None, depth: int = 3, context=None, **kw):  # ⟲
    return SR.op_recurse(expr, depth, context or {})

def _h_project(ctx, expr=None, index: int = 0, context=None, **kw):  # π
    return SR.op_project(expr, index, context or {})

# --------------------------
# Safe registration helpers
# --------------------------

def _safe_register(symbol: str, handler: Callable[..., Any], domain: str):
    """Register domain-tagged key; alias raw symbol if new."""
    key = f"{domain}:{symbol}"
    try:
        registry.register(key, handler)
        registry.alias(symbol, key)
    except ValueError:
        # already registered
        pass


# --------------------------
# Bind symatics symbols
# --------------------------

_safe_register("⊕", _h_superpose, "symatics")
_safe_register("μ", _h_measure, "symatics")
_safe_register("↔", _h_entangle, "symatics")
_safe_register("⟲", _h_recurse, "symatics")
_safe_register("π", _h_project, "symatics")


# --------------------------
# Bind physics symbols
# --------------------------

_safe_register("∇", _h_grad, "physics")
_safe_register("∇·", _h_div, "physics")
_safe_register("∇×", _h_curl, "physics")
_safe_register("Δ", _h_laplacian, "physics")
_safe_register("d/dt", _h_d_dt, "physics")

_safe_register("•", _h_dot, "physics")
_safe_register("×", _h_cross, "physics")
_safe_register("⊗", _h_tensor, "physics")

_safe_register("ℏ", _h_hbar, "physics")
_safe_register("iħ∂/∂t", _h_schrod, "physics")
_safe_register("□", _h_box, "physics")
_safe_register("∂_μ", _h_partial_mu, "physics")
_safe_register("∇_μ", _h_nabla_mu, "physics")

# Aliases (ASCII etc.)
_safe_register("GRAD", _h_grad, "physics")
_safe_register("DIV", _h_div, "physics")
_safe_register("CURL", _h_curl, "physics")
_safe_register("LAPL", _h_laplacian, "physics")
_safe_register("DDT", _h_d_dt, "physics")
_safe_register("DOT", _h_dot, "physics")
_safe_register("CROSS", _h_cross, "physics")
_safe_register("TENSOR", _h_tensor, "physics")
_safe_register("·", _h_dot, "physics")
_safe_register("∂t", _h_d_dt, "physics")


# --------------------------
# Glyph Operator Handlers (Phase 9 Migration)
# --------------------------

def _glyph_teleport(ctx, target=None, **kw):
    if not target:
        return {"status": "error", "error": "No destination"}
    if not hasattr(ctx, "teleport"):
        return {"status": "error", "error": "No state manager for teleport"}
    ctx.teleport(target)
    return {"status": "ok", "teleported_to": target}

def _glyph_write_cube(ctx, target=None, value="⛓️", meta=None, **kw):
    if not target or len(target) != 3:
        return {"status": "error", "error": "Invalid coordinates"}
    x, y, z = target
    container = ctx.get_current_container() if hasattr(ctx, "get_current_container") else None
    container_path = container.get("path") if container else None
    if container_path:
        from backend.modules.dna_chain.dc_handler import carve_glyph_cube
        carve_glyph_cube(container_path, f"{x},{y},{z}", value, meta or {})
        return {"status": "ok", "coords": (x, y, z), "value": value}
    return {"status": "error", "error": "No container path"}

def _glyph_run_mutation(ctx, module=None, reason="No reason provided.", **kw):
    if not module:
        return {"status": "error", "error": "Missing module name"}
    from backend.modules.dna_chain.crispr_ai import generate_mutation_proposal
    generate_mutation_proposal(module, reason)
    return {"status": "ok", "mutation_module": module}

def _glyph_rewrite(ctx, target=None, **kw):
    if not target or len(target) != 3:
        return {"status": "error", "error": "Invalid coordinates"}
    x, y, z = target
    coord_str = f"{x},{y},{z}"
    container = ctx.get_current_container() if hasattr(ctx, "get_current_container") else None
    container_path = container.get("path") if container else None
    if container_path:
        from backend.modules.glyphos.glyph_mutator import run_self_rewrite
        success = run_self_rewrite(container_path, coord_str)
        if success:
            return {"status": "ok", "rewritten": coord_str}
        return {"status": "skipped", "coord": coord_str}
    return {"status": "error", "error": "No container path"}

def _glyph_log(ctx, message="No message.", **kw):
    return {"status": "ok", "log": message}


# Register glyph ops in registry
_safe_register("teleport", _glyph_teleport, "glyph")
_safe_register("write_cube", _glyph_write_cube, "glyph")
_safe_register("run_mutation", _glyph_run_mutation, "glyph")
_safe_register("rewrite", _glyph_rewrite, "glyph")
_safe_register("log", _glyph_log, "glyph")


# --------------------------
# Logic Negation Example
# --------------------------

def _h_negation(_ctx, x=None, context=None, **_kw):
    return {"neg": x}

_safe_register("¬", _h_negation, "logic")


# -----------------------------------------------------------------------------
# Legacy alias overrides (ensure canonical domain mapping wins over symatics)
# -----------------------------------------------------------------------------
registry.aliases.update({
    "⊕": "logic:⊕",       # addition / combine
    "⟲": "control:⟲",     # loop / iteration
    "→": "logic:→",       # sequence / trigger
})

# --------------------------
# Metadata (canonical + aliases)
# --------------------------

INSTRUCTION_METADATA: Dict[str, Dict[str, str]] = {
    # --------------------------
    # Physics Operators
    # --------------------------
    "physics:∇":    {"type": "physics_op", "impl": "gradient_operator"},
    "physics:∇·":   {"type": "physics_op", "impl": "divergence_operator"},
    "physics:∇×":   {"type": "physics_op", "impl": "curl_operator"},
    "physics:Δ":    {"type": "physics_op", "impl": "laplacian_operator"},
    "physics:⊗":    {"type": "physics_op", "impl": "tensor_product"},
    "physics:×":    {"type": "physics_op", "impl": "cross_product"},
    "physics:•":    {"type": "physics_op", "impl": "dot_product"},
    "physics:□":    {"type": "physics_op", "impl": "dalembertian_operator"},
    "physics:d/dt": {"type": "physics_op", "impl": "time_derivative"},
    "physics:∂_μ":  {"type": "physics_op", "impl": "partial_derivative"},
    "physics:∇_μ":  {"type": "physics_op", "impl": "covariant_derivative"},
    "physics:ℏ":    {"type": "physics_op", "impl": "planck_constant"},
    "physics:iħ∂/∂t": {"type": "physics_op", "impl": "schrodinger_operator"},

    # Aliases (ASCII etc.)
    "physics:GRAD":   {"type": "physics_op", "impl": "gradient_operator"},
    "physics:DIV":    {"type": "physics_op", "impl": "divergence_operator"},
    "physics:CURL":   {"type": "physics_op", "impl": "curl_operator"},
    "physics:LAPL":   {"type": "physics_op", "impl": "laplacian_operator"},
    "physics:DDT":    {"type": "physics_op", "impl": "time_derivative"},
    "physics:DOT":    {"type": "physics_op", "impl": "dot_product"},
    "physics:CROSS":  {"type": "physics_op", "impl": "cross_product"},
    "physics:TENSOR": {"type": "physics_op", "impl": "tensor_product"},
    "physics:·":      {"type": "physics_op", "impl": "dot_product"},
    "physics:∂t":     {"type": "physics_op", "impl": "time_derivative"},

    # --------------------------
    # Symatics Operators
    # --------------------------
    "symatics:⊕": {"type": "symatics_op", "impl": "superpose"},
    "symatics:μ": {"type": "symatics_op", "impl": "measure"},
    "symatics:↔": {"type": "symatics_op", "impl": "entangle"},
    "symatics:⟲": {"type": "symatics_op", "impl": "recurse"},
    "symatics:π": {"type": "symatics_op", "impl": "project"},

    # --------------------------
    # Logic / Control / Memory
    # --------------------------
    "logic:→":   {"type": "logic_op", "impl": "sequence"},
    "logic:⊕":   {"type": "logic_op", "impl": "store"},
    "logic:¬":   {"type": "logic_op", "impl": "negation"},
    "control:⟲": {"type": "control_op", "impl": "reflect"},
    "memory:↺":  {"type": "memory_op", "impl": "recall"},

    # --------------------------
    # Glyph Operators
    # --------------------------
    "glyph:teleport": {
        "type": "glyph_op",
        "impl": "teleport",
        "desc": "Teleport state/context to a target container or location."
    },
    "glyph:write_cube": {
        "type": "glyph_op",
        "impl": "write_cube",
        "desc": "Carve or write a glyph into a spatial cube coordinate."
    },
    "glyph:run_mutation": {
        "type": "glyph_op",
        "impl": "run_mutation",
        "desc": "Trigger CRISPR mutation proposal pipeline for a module."
    },
    "glyph:rewrite": {
        "type": "glyph_op",
        "impl": "rewrite",
        "desc": "Self-rewrite a glyph cube at a coordinate."
    },
    "glyph:log": {
        "type": "glyph_op",
        "impl": "log",
        "desc": "Emit a log message into glyph stream."
    },
}

# -----------------------------------------------------------------------------
# Canonical Symbolic Opcode wrapper
# -----------------------------------------------------------------------------
class SymbolicOpCode(str):
    """
    Wrapper for symbolic operation keys.
    Normalizes glyphs using the registry or alias shim.
    """
    def __new__(cls, symbol: str):
        try:
            canonical = registry.get_opcode(symbol)
        except Exception:
            canonical = symbol
        return str.__new__(cls, canonical)


# -----------------------------------------------------------------------------
# Handler Mapping (used by VirtualCPUBeamCore)
# -----------------------------------------------------------------------------
OPCODE_HANDLER_MAP = {
    SymbolicOpCode("⊕"): "handle_add",
    SymbolicOpCode("→"): "handle_sequence",
    SymbolicOpCode("↔"): "handle_bidir",
    SymbolicOpCode("⟲"): "handle_loop",
    SymbolicOpCode("⧖"): "handle_delay",
    SymbolicOpCode("≡"): "handle_store",
    SymbolicOpCode("✦"): "handle_dream",
    SymbolicOpCode("⧠"): "handle_q_entangle",
    SymbolicOpCode("⧝"): "handle_q_collapse",
}