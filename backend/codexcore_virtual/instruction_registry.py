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

    def execute(self, key: str, operand: Any) -> Any:
        """
        Back-compat single-operand entrypoint.
        Redirects raw glyphs via alias shim.
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

        if isinstance(operand, dict):
            if "args" in operand or "kwargs" in operand:
                args = operand.get("args", [])
                kwargs = operand.get("kwargs", {})
                return fn(None, *args, **kwargs)  # ctx=None
            return fn(None, **operand)

        return fn(None, operand)

    def execute_v2(self, key: str, *args, **kwargs) -> Any:
        """Modern var-arg entrypoint (preferred)."""
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
        return self.registry[key](None, *args, **kwargs)


# Global default registry
registry = InstructionRegistry()

# --------------------------
# Simple built-in handlers
# --------------------------

def handle_reflect(_ctx, data=None, **_kw):
    return f"[REFLECT] {data}"

def handle_store(_ctx, data=None, **_kw):
    return f"[STORE] {data}"

def handle_recall(_ctx, data=None, **_kw):
    return f"[RECALL] {data}"

def handle_sequence(_ctx, left=None, right=None, **_kw):
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
def _h_grad(ctx, field=None, coords=None, **kw):      # ∇
    _need_pk("∇")
    return _to_python(PK.grad(field, coords))

def _h_div(ctx, vec=None, coords=None, **kw):        # ∇·
    _need_pk("∇·")
    return _to_python(PK.div(vec, coords))

def _h_curl(ctx, vec=None, coords=None, **kw):       # ∇×
    _need_pk("∇×")
    return _to_python(PK.curl(vec, coords))

def _h_laplacian(ctx, field=None, coords=None, **kw):  # Δ
    _need_pk("Δ")
    return _to_python(PK.laplacian(field, coords))

def _h_d_dt(ctx, expr=None, t: Optional[str] = None, **kw):  # d/dt
    _need_pk("d/dt")
    return _to_python(PK.d_dt(expr, t or "t"))

# Linear algebra / tensor ops
def _h_dot(ctx, A=None, B=None, **kw):               # •
    _need_pk("•")
    return _to_python(PK.dot(A, B))

def _h_cross(ctx, A=None, B=None, **kw):             # ×
    _need_pk("×")
    return _to_python(PK.cross(A, B))

def _h_tensor(ctx, A=None, B=None, **kw):            # ⊗
    _need_pk("⊗")
    return _to_python(PK.tensor_product(A, B))

# Quantum / wave ops
def _h_hbar(ctx, **kw):                               # ℏ
    _need_pk("ℏ")
    if hasattr(PK, "hbar"):
        return _to_python(PK.hbar())
    raise NotImplementedError

def _h_schrod(ctx, psi=None, H=None, t: Optional[str] = None, **kw):  # iħ∂/∂t
    _need_pk("iħ∂/∂t")
    if hasattr(PK, "schrodinger"):
        return _to_python(PK.schrodinger(psi, H, t or "t"))
    raise NotImplementedError

def _h_box(ctx, field=None, coords=None, metric=None, **kw):  # □
    _need_pk("□")
    if hasattr(PK, "dalembertian"):
        return _to_python(PK.dalembertian(field, coords=coords, metric=metric))
    raise NotImplementedError

def _h_partial_mu(ctx, field=None, mu=None, coords=None, **kw):  # ∂_μ
    _need_pk("∂_μ")
    if hasattr(PK, "partial_mu"):
        return _to_python(PK.partial_mu(field, mu=mu, coords=coords))
    raise NotImplementedError

def _h_nabla_mu(ctx, field=None, mu=None, metric=None, connection=None, **kw):  # ∇_μ
    _need_pk("∇_μ")
    if hasattr(PK, "nabla_mu"):
        return _to_python(PK.nabla_mu(field, mu=mu, metric=metric, connection=connection))
    raise NotImplementedError

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
        pass

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
# Logic Negation Example
# --------------------------

def _h_negation(_ctx, x=None, **_kw):
    return {"neg": x}
_safe_register("¬", _h_negation, "logic")

# --------------------------
# Metadata
# --------------------------

INSTRUCTION_METADATA: Dict[str, Dict[str, str]] = {
    "physics:∇":  {"type": "physics_op", "impl": "gradient_operator"},
    "physics:∇·": {"type": "physics_op", "impl": "divergence_operator"},
    "physics:∇×": {"type": "physics_op", "impl": "curl_operator"},
    "physics:Δ":  {"type": "physics_op", "impl": "laplacian_operator"},
    "physics:⊗":  {"type": "physics_op", "impl": "tensor_product"},
    "physics:×":  {"type": "physics_op", "impl": "cross_product"},
    "physics:•":  {"type": "physics_op", "impl": "dot_product"},
    "physics:□":  {"type": "physics_op", "impl": "dalembertian_operator"},
}