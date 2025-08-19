from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Tuple, Optional, Union

from backend.modules.symbolic_engine.symbolic_ingestion_engine import SymbolicIngestionEngine

Scalar = Union[float, int, str, Dict[str, Any]]
Vector = Dict[str, Any]  # symbolic vector/tensor node form used across kernels


@dataclass
class GlyphNode:
    """Generic symbolic node (keeps everything in the same tree style as math/logic kernels)."""
    op: str
    args: Tuple[Any, ...]
    meta: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "GlyphNode",
            "op": self.op,
            "args": [a.to_dict() if isinstance(a, GlyphNode) else a for a in self.args],
            "meta": self.meta or {},
        }


# ---------- Helpers ----------

def is_symbolic(x: Any) -> bool:
    return isinstance(x, GlyphNode) or isinstance(x, dict)

def sym(op: str, *args: Any, **meta: Any) -> GlyphNode:
    return GlyphNode(op=op, args=args, meta=meta or None)


# ---------- Core vector/tensor field ops ----------

def grad(field: Scalar, coords: Tuple[str, ...] = ("x", "y", "z")) -> GlyphNode:
    """∇f → gradient (symbolic)"""
    node = sym("∇", field, coords)
    SymbolicIngestionEngine.ingest_data(
        {
            "op": "grad",
            "args": [field, coords],
            "codexlang": f"grad({field})",
            "glyph": node.to_dict(),
            "domain": "physics.vector"
        },
        source="PhysicsKernel",
        tags=["physics", "grad"]
    )
    return node

def div(vec: Vector, coords: Tuple[str, ...] = ("x", "y", "z")) -> GlyphNode:
    """∇·V → divergence (symbolic)"""
    node = sym("∇·", vec, coords)
    SymbolicIngestionEngine.ingest_data(
        {
            "op": "div",
            "args": [vec, coords],
            "codexlang": f"div({vec})",
            "glyph": node.to_dict(),
            "domain": "physics.vector"
        },
        source="PhysicsKernel",
        tags=["physics", "div"]
    )
    return node

def curl(vec: Vector, coords: Tuple[str, ...] = ("x", "y", "z")) -> GlyphNode:
    """∇×V → curl (symbolic)"""
    node = sym("∇×", vec, coords)
    SymbolicIngestionEngine.ingest_data(
        {
            "op": "curl",
            "args": [vec, coords],
            "codexlang": f"curl({vec})",
            "glyph": node.to_dict(),
            "domain": "physics.vector"
        },
        source="PhysicsKernel",
        tags=["physics", "curl"]
    )
    return node

def laplacian(field: Scalar, coords: Tuple[str, ...] = ("x", "y", "z")) -> GlyphNode:
    """Δf (∇²f) → Laplacian (symbolic)"""
    node = sym("Δ", field, coords)
    SymbolicIngestionEngine.ingest_data(
        {
            "op": "laplacian",
            "args": [field, coords],
            "codexlang": f"laplacian({field})",
            "glyph": node.to_dict(),
            "domain": "physics.vector"
        },
        source="PhysicsKernel",
        tags=["physics", "laplacian"]
    )
    return node

def d_dt(expr: Any, t: str = "t") -> GlyphNode:
    """d/dt (time derivative)"""
    return sym("d/dt", expr, t)

def tensor_product(a: Any, b: Any) -> GlyphNode:
    return sym("⊗", a, b)

def dot(a: Any, b: Any) -> GlyphNode:
    return sym("·", a, b)

def cross(a: Any, b: Any) -> GlyphNode:
    return sym("×", a, b)


# ---------- Quantum glyphs (symbolic) ----------

def ket(label: str) -> GlyphNode:
    return sym("|ψ⟩", label)

def bra(label: str) -> GlyphNode:
    return sym("⟨ψ|", label)

def operator(name: str, arg: Any = None) -> GlyphNode:
    return sym("Â", name, arg)

def hamiltonian(H_name: str = "H") -> GlyphNode:
    return sym("H", H_name)

def commutator(A: Any, B: Any) -> GlyphNode:
    return sym("[ , ]", A, B)

def schrodinger_evolution(psi: Any, H: Any, t: str = "t") -> GlyphNode:
    """iℏ ∂|ψ⟩/∂t = H|ψ⟩  (symbolic statement)"""
    lhs = sym("·", "iℏ", d_dt(psi, t))
    rhs = sym("·", H, psi)
    node = sym("≐", lhs, rhs, equation="Schr")

    SymbolicIngestionEngine.ingest_data(
        {
            "op": "schrodinger_evolution",
            "args": [psi, H, t],
            "codexlang": f"evolve({psi}, {H}, {t})",
            "glyph": node.to_dict(),
            "domain": "physics.quantum"
        },
        source="PhysicsKernel",
        tags=["physics", "quantum"]
    )
    return node


# ---------- GR glyphs (symbolic) ----------

def metric(g_symbol: str = "g") -> GlyphNode:
    return sym("g_{μν}", g_symbol)

def inverse_metric(g_inv_symbol: str = "g^{-1}") -> GlyphNode:
    return sym("g^{μν}", g_inv_symbol)

def covariant_derivative(expr: Any, index: str = "μ") -> GlyphNode:
    return sym("∇_μ", expr, index)

def riemann() -> GlyphNode:
    return sym("R^ρ_{σμν}")

def ricci() -> GlyphNode:
    return sym("R_{μν}")

def ricci_scalar() -> GlyphNode:
    return sym("R")

def stress_energy(T: str = "T_{μν}") -> GlyphNode:
    return sym("T_{μν}", T)

def einstein_equation(G: Any, T: Any) -> GlyphNode:
    """G_{μν} = 8πG T_{μν}   (symbolic)"""
    node = sym("≐", G, sym("·", "8πG", T), equation="Einstein")
    SymbolicIngestionEngine.ingest_data(
        {
            "op": "einstein_equation",
            "args": [G, T],
            "codexlang": f"{G} = 8πG * {T}",
            "glyph": node.to_dict(),
            "domain": "physics.relativity"
        },
        source="PhysicsKernel",
        tags=["physics", "relativity"]
    )
    return node

def einstein_tensor() -> GlyphNode:
    return sym("G_{μν}")


# ---------- Registry (so other modules can “discover” physics ops) ----------

REGISTRY: Dict[str, Any] = {
    # vector/tensor calculus
    "grad": grad,
    "div": div,
    "curl": curl,
    "laplacian": laplacian,
    "d_dt": d_dt,
    "tensor_product": tensor_product,
    "dot": dot,
    "cross": cross,

    # quantum
    "ket": ket,
    "bra": bra,
    "operator": operator,
    "hamiltonian": hamiltonian,
    "commutator": commutator,
    "schrodinger_evolution": schrodinger_evolution,

    # GR
    "metric": metric,
    "inverse_metric": inverse_metric,
    "covariant_derivative": covariant_derivative,
    "riemann": riemann,
    "ricci": ricci,
    "ricci_scalar": ricci_scalar,
    "stress_energy": stress_energy,
    "einstein_tensor": einstein_tensor,
    "einstein_equation": einstein_equation,
}

def get_registry() -> Dict[str, Any]:
    return dict(REGISTRY)