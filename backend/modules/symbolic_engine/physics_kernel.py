from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Tuple, Optional, Union

from backend.modules.symbolic_engine.symbolic_ingestion_engine import SymbolicIngestionEngine
from backend.modules.knowledge_graph.kg_writer_singleton import kg_writer

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


def is_symbolic(x: Any) -> bool:
    return isinstance(x, GlyphNode) or isinstance(x, dict)


def sym(op: str, *args: Any, **meta: Any) -> GlyphNode:
    return GlyphNode(op=op, args=args, meta=meta or None)


class PhysicsKernel:
    def __init__(self, container_id: Optional[str] = None):
        self.container_id = container_id or "physics_kernel_default"
        self.kg_writer = kg_writer
        self.ingestion_engine = SymbolicIngestionEngine()

    def write_glyph_to_kg(self, glyph):
        self.kg_writer.write(glyph.to_dict())

    # ---------- Vector/Tensor Field Ops ----------

    def grad(self, field: Scalar, coords: Tuple[str, ...] = ("x", "y", "z")) -> GlyphNode:
        node = sym("∇", field, coords)
        self.ingestion_engine.ingest_data(
            {
                "op": "grad",
                "args": [field, coords],
                "codexlang": f"grad({field})",
                "glyph": node.to_dict(),
                "domain": "physics.vector",
                "container": self.container_id,
            },
            source="PhysicsKernel",
            tags=["physics", "grad"]
        )
        return node

    def div(self, vec: Vector, coords: Tuple[str, ...] = ("x", "y", "z")) -> GlyphNode:
        node = sym("∇·", vec, coords)
        self.ingestion_engine.ingest_data(
            {
                "op": "div",
                "args": [vec, coords],
                "codexlang": f"div({vec})",
                "glyph": node.to_dict(),
                "domain": "physics.vector",
                "container": self.container_id,
            },
            source="PhysicsKernel",
            tags=["physics", "div"]
        )
        return node

    def curl(self, vec: Vector, coords: Tuple[str, ...] = ("x", "y", "z")) -> GlyphNode:
        node = sym("∇×", vec, coords)
        self.ingestion_engine.ingest_data(
            {
                "op": "curl",
                "args": [vec, coords],
                "codexlang": f"curl({vec})",
                "glyph": node.to_dict(),
                "domain": "physics.vector",
                "container": self.container_id,
            },
            source="PhysicsKernel",
            tags=["physics", "curl"]
        )
        return node

    def laplacian(self, field: Scalar, coords: Tuple[str, ...] = ("x", "y", "z")) -> GlyphNode:
        node = sym("Δ", field, coords)
        self.ingestion_engine.ingest_data(
            {
                "op": "laplacian",
                "args": [field, coords],
                "codexlang": f"laplacian({field})",
                "glyph": node.to_dict(),
                "domain": "physics.vector",
                "container": self.container_id,
            },
            source="PhysicsKernel",
            tags=["physics", "laplacian"]
        )
        return node

    def d_dt(self, expr: Any, t: str = "t") -> GlyphNode:
        return sym("d/dt", expr, t)

    def tensor_product(self, a: Any, b: Any) -> GlyphNode:
        return sym("⊗", a, b)

    def dot(self, a: Any, b: Any) -> GlyphNode:
        return sym("·", a, b)

    def cross(self, a: Any, b: Any) -> GlyphNode:
        return sym("×", a, b)

    # ---------- Quantum Glyphs ----------

    def ket(self, label: str) -> GlyphNode:
        return sym("|ψ⟩", label)

    def bra(self, label: str) -> GlyphNode:
        return sym("⟨ψ|", label)

    def operator(self, name: str, arg: Any = None) -> GlyphNode:
        return sym("Â", name, arg)

    def hamiltonian(self, H_name: str = "H") -> GlyphNode:
        return sym("H", H_name)

    def commutator(self, A: Any, B: Any) -> GlyphNode:
        return sym("[ , ]", A, B)

    def schrodinger_evolution(self, psi: Any, H: Any, t: str = "t") -> GlyphNode:
        lhs = self.dot("iℏ", self.d_dt(psi, t))
        rhs = self.dot(H, psi)
        node = sym("≐", lhs, rhs, equation="Schr")

        self.ingestion_engine.ingest_data(
            {
                "op": "schrodinger_evolution",
                "args": [psi, H, t],
                "codexlang": f"evolve({psi}, {H}, {t})",
                "glyph": node.to_dict(),
                "domain": "physics.quantum",
                "container": self.container_id,
            },
            source="PhysicsKernel",
            tags=["physics", "quantum"]
        )
        return node

    # ---------- General Relativity Glyphs ----------

    def metric(self, g_symbol: str = "g") -> GlyphNode:
        return sym("g_{μν}", g_symbol)

    def inverse_metric(self, g_inv_symbol: str = "g^{-1}") -> GlyphNode:
        return sym("g^{μν}", g_inv_symbol)

    def covariant_derivative(self, expr: Any, index: str = "μ") -> GlyphNode:
        return sym("∇_μ", expr, index)

    def riemann(self) -> GlyphNode:
        return sym("R^ρ_{σμν}")

    def ricci(self) -> GlyphNode:
        return sym("R_{μν}")

    def ricci_scalar(self) -> GlyphNode:
        return sym("R")

    def stress_energy(self, T: str = "T_{μν}") -> GlyphNode:
        return sym("T_{μν}", T)

    def einstein_tensor(self) -> GlyphNode:
        return sym("G_{μν}")

    def einstein_equation(self, G: Any, T: Any) -> GlyphNode:
        node = sym("≐", G, sym("·", "8πG", T), equation="Einstein")

        self.ingestion_engine.ingest_data(
            {
                "op": "einstein_equation",
                "args": [G, T],
                "codexlang": f"{G} = 8πG * {T}",
                "glyph": node.to_dict(),
                "domain": "physics.relativity",
                "container": self.container_id,
            },
            source="PhysicsKernel",
            tags=["physics", "relativity"]
        )
        return node


# ---------- Public Registry ----------

DEFAULT_KERNEL = PhysicsKernel()

REGISTRY: Dict[str, Any] = {
    # vector/tensor calculus
    "grad": DEFAULT_KERNEL.grad,
    "div": DEFAULT_KERNEL.div,
    "curl": DEFAULT_KERNEL.curl,
    "laplacian": DEFAULT_KERNEL.laplacian,
    "d_dt": DEFAULT_KERNEL.d_dt,
    "tensor_product": DEFAULT_KERNEL.tensor_product,
    "dot": DEFAULT_KERNEL.dot,
    "cross": DEFAULT_KERNEL.cross,

    # quantum
    "ket": DEFAULT_KERNEL.ket,
    "bra": DEFAULT_KERNEL.bra,
    "operator": DEFAULT_KERNEL.operator,
    "hamiltonian": DEFAULT_KERNEL.hamiltonian,
    "commutator": DEFAULT_KERNEL.commutator,
    "schrodinger_evolution": DEFAULT_KERNEL.schrodinger_evolution,

    # GR
    "metric": DEFAULT_KERNEL.metric,
    "inverse_metric": DEFAULT_KERNEL.inverse_metric,
    "covariant_derivative": DEFAULT_KERNEL.covariant_derivative,
    "riemann": DEFAULT_KERNEL.riemann,
    "ricci": DEFAULT_KERNEL.ricci,
    "ricci_scalar": DEFAULT_KERNEL.ricci_scalar,
    "stress_energy": DEFAULT_KERNEL.stress_energy,
    "einstein_tensor": DEFAULT_KERNEL.einstein_tensor,
    "einstein_equation": DEFAULT_KERNEL.einstein_equation,
}


def get_registry() -> Dict[str, Any]:
    return dict(REGISTRY)