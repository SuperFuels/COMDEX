# -*- coding: utf-8 -*-
# File: backend/modules/codexcore_virtual/instruction_registry.py
"""
Instruction Registry for Virtual CodexCore

- Maps CodexLang symbolic operators to runtime handlers.
- Supports multi-argument calls, kwargs, and hot overrides.
- Backward compatible with the original single-operand API.
- Includes optional physics operators (grad, div, curl, etc.) that
  call into backend.modules.symbolic_engine.physics_kernel (if present).

If a physics symbol is already registered elsewhere, we **do not** overwrite it
(unless you call registry.override yourself).
"""

from typing import Callable, Dict, Any, Optional

# --------------------------
# Core Instruction Registry
# --------------------------

class InstructionRegistry:
    def __init__(self):
        # Handlers take signature: handler(ctx, *args, **kwargs) -> Any
        self.registry: Dict[str, Callable[..., Any]] = {}

    def register(self, symbol: str, handler: Callable[..., Any]):
        if symbol in self.registry:
            raise ValueError(f"Instruction '{symbol}' already registered.")
        self.registry[symbol] = handler

    def override(self, symbol: str, handler: Callable[..., Any]):
        """Force override (useful for mutation/hot patching)."""
        self.registry[symbol] = handler

    def list_instructions(self) -> Dict[str, str]:
        return {symbol: func.__name__ for symbol, func in self.registry.items()}

    # --- Execution APIs ---

    def execute(self, symbol: str, operand: Any) -> Any:
        """
        Back-compat single-operand entrypoint.
        If 'operand' is a dict, we will unpack it into *args/**kwargs automatically:
          - If it contains "args"/"kwargs" keys, we use those.
          - Else we treat it as **kwargs.

        Returns the handler result as-is.
        """
        if symbol not in self.registry:
            raise KeyError(f"Unknown instruction symbol: {symbol}")
        fn = self.registry[symbol]

        if isinstance(operand, dict):
            if "args" in operand or "kwargs" in operand:
                args = operand.get("args", [])
                kwargs = operand.get("kwargs", {})
                return fn(None, *args, **kwargs)  # ctx=None
            return fn(None, **operand)  # treat dict as kwargs

        # Legacy: single positional
        return fn(None, operand)

    def execute_v2(self, symbol: str, *args, **kwargs) -> Any:
        """Modern var-arg entrypoint (preferred in new code)."""
        if symbol not in self.registry:
            raise KeyError(f"Unknown instruction symbol: {symbol}")
        return self.registry[symbol](None, *args, **kwargs)


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

# Preserve your original defaults
registry.register("⟲", handle_reflect)
registry.register("⊕", handle_store)
registry.register("↺", handle_recall)

# ---------------------------------
# Optional Physics Operator Handlers
# ---------------------------------

def _to_python(obj: Any) -> Any:
    """Best-effort: return dict if the object exposes to_dict(); else return as-is."""
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
    # Lazy import so this file works even if physics kernel isn’t present yet.
    from backend.modules.symbolic_engine import physics_kernel as PK
except Exception:
    PK = None  # Handlers will raise helpful errors if called

def _need_pk(name: str):
    if PK is None:
        raise RuntimeError(
            f"physics_kernel not available; cannot execute '{name}'. "
            "Add backend/modules/symbolic_engine/physics_kernel.py or adjust your imports."
        )

# Vector calculus
def _h_grad(ctx, field=None, coords=None, **kw):      # ∇
    _need_pk("∇ (grad)")
    return _to_python(PK.grad(field, coords))

def _h_div(ctx, vec=None, coords=None, **kw):        # ∇·
    _need_pk("∇· (div)")
    return _to_python(PK.div(vec, coords))

def _h_curl(ctx, vec=None, coords=None, **kw):       # ∇×
    _need_pk("∇× (curl)")
    return _to_python(PK.curl(vec, coords))

def _h_laplacian(ctx, field=None, coords=None, **kw):  # Δ
    _need_pk("Δ (laplacian)")
    return _to_python(PK.laplacian(field, coords))

def _h_d_dt(ctx, expr=None, t: Optional[str] = None, **kw):  # d/dt
    _need_pk("d/dt (time derivative)")
    return _to_python(PK.d_dt(expr, t or "t"))

# Linear algebra / tensor ops
def _h_dot(ctx, A=None, B=None, **kw):               # •
    _need_pk("• (dot)")
    return _to_python(PK.dot(A, B))

def _h_cross(ctx, A=None, B=None, **kw):             # ×
    _need_pk("× (cross)")
    return _to_python(PK.cross(A, B))

def _h_tensor(ctx, A=None, B=None, **kw):            # ⊗
    _need_pk("⊗ (tensor product)")
    return _to_python(PK.tensor_product(A, B))

# Quantum / wave ops (registered only if available in PK)
def _h_hbar(ctx, **kw):                               # ℏ
    _need_pk("ℏ")
    if hasattr(PK, "hbar"):
        return _to_python(PK.hbar())
    raise NotImplementedError("PK.hbar() not implemented")

def _h_schrod(ctx, psi=None, H=None, t: Optional[str] = None, **kw):  # iħ∂/∂t
    _need_pk("iħ∂/∂t (Schrödinger)")
    if hasattr(PK, "schrodinger"):
        return _to_python(PK.schrodinger(psi, H, t or "t"))
    raise NotImplementedError("PK.schrodinger(psi, H, t) not implemented")

def _h_box(ctx, field=None, coords=None, metric=None, **kw):  # □ (d'Alembertian)
    _need_pk("□ (d'Alembertian)")
    if hasattr(PK, "dalembertian"):
        return _to_python(PK.dalembertian(field, coords=coords, metric=metric))
    raise NotImplementedError("PK.dalembertian(field, coords, metric) not implemented")

# GR / covariant derivatives (registered only if available)
def _h_partial_mu(ctx, field=None, mu=None, coords=None, **kw):  # ∂_μ
    _need_pk("∂_μ")
    if hasattr(PK, "partial_mu"):
        return _to_python(PK.partial_mu(field, mu=mu, coords=coords))
    raise NotImplementedError("PK.partial_mu(field, mu, coords) not implemented")

def _h_nabla_mu(ctx, field=None, mu=None, metric=None, connection=None, **kw):  # ∇_μ
    _need_pk("∇_μ")
    if hasattr(PK, "nabla_mu"):
        return _to_python(PK.nabla_mu(field, mu=mu, metric=metric, connection=connection))
    raise NotImplementedError("PK.nabla_mu(field, mu, metric, connection) not implemented")

# --------------------------
# Safe registration helpers
# --------------------------

def _safe_register(symbol: str, handler: Callable[..., Any]):
    """Register only if not already taken; print a gentle note otherwise."""
    try:
        registry.register(symbol, handler)
    except ValueError:
        # Symbol already registered elsewhere; keep existing binding.
        # If you *want* to force the new handler, call: registry.override(symbol, handler)
        # We avoid noisy logs by default; uncomment if you want visibility:
        # print(f"[info] Symbol '{symbol}' already registered; skipping physics binding.")
        pass

# --------------------------
# CodexLang Command Shim
# --------------------------

def register_codex_command(symbol: str):
    """
    Decorator to register a CodexLang command using the InstructionRegistry.
    Equivalent to: registry.register(symbol, fn)
    """
    def decorator(fn):
        registry.register(symbol, fn)
        return fn
    return decorator

def execute_codex_command(symbol: str, operand: Any) -> Any:
    """
    Backward-compatible execution interface for CodexLang.
    """
    return registry.execute(symbol, operand)

def execute_codex_command_v2(symbol: str, *args, **kwargs) -> Any:
    """
    Modern CodexLang multi-argument execution wrapper.
    """
    return registry.execute_v2(symbol, *args, **kwargs)

def override_codex_command(symbol: str, fn):
    """
    Force override of a CodexLang command.
    """
    registry.override(symbol, fn)

def get_registered_codex_commands():
    """
    Returns a dict of all registered CodexLang command names to function names.
    """
    return registry.list_instructions()

# --------------------------
# Bind physics symbols
# --------------------------

# Vector calculus
_safe_register("∇", _h_grad)        # gradient
_safe_register("∇·", _h_div)        # divergence
_safe_register("∇×", _h_curl)       # curl
_safe_register("Δ", _h_laplacian)   # Laplacian
_safe_register("d/dt", _h_d_dt)     # time derivative

# Linear algebra / tensor
_safe_register("•", _h_dot)         # dot product
_safe_register("×", _h_cross)       # cross product
_safe_register("⊗", _h_tensor)      # tensor product (will be skipped if ⊗ already used elsewhere)

# Quantum / wave / GR (only work if physics_kernel provides the functions)
_safe_register("ℏ", _h_hbar)
_safe_register("iħ∂/∂t", _h_schrod)
_safe_register("□", _h_box)
_safe_register("∂_μ", _h_partial_mu)
_safe_register("∇_μ", _h_nabla_mu)

# --------------------------
# ASCII aliases & negation
# --------------------------

# Reuse the existing physics handlers defined above:
#   _h_grad, _h_div, _h_curl, _h_laplacian, _h_d_dt,
#   _h_dot, _h_cross, _h_tensor

# ASCII / mnemonic aliases
_safe_register("GRAD",   _h_grad)
_safe_register("DIV",    _h_div)
_safe_register("CURL",   _h_curl)
_safe_register("LAPL",   _h_laplacian)
_safe_register("DDT",    _h_d_dt)          # time derivative
_safe_register("DOT",    _h_dot)
_safe_register("CROSS",  _h_cross)
_safe_register("TENSOR", _h_tensor)

# Accept both "·" and "•" for dot, and both "d/dt" and "∂t" for time-derivative
_safe_register("·",      _h_dot)
_safe_register("d/dt",   _h_d_dt)
_safe_register("∂t",     _h_d_dt)

# If you want to **force** ⊗ to be the tensor product (overriding any prior meaning):
# (Comment this out if you prefer the current binding.)
registry.override("⊗", _h_tensor)

# Provide a simple logical negation on '¬' (hook to your logic kernel later if needed)
def _h_negation(_ctx, x=None, **_kw):
    return {"neg": x}
_safe_register("¬", _h_negation)

# --------------------------
# Notes:
# - If you want these physics handlers to **always** win, replace `_safe_register`
#   with `registry.override(symbol, handler)` per symbol.
# - From your Codex executor, you can now call either:
#     registry.execute("∇", {"field": F, "coords": ["x","y","z"]})
#   or:
#     registry.execute_v2("∇", field=F, coords=["x","y","z"])
# --------------------------