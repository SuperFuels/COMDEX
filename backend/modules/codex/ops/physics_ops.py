# backend/modules/codex/ops/physics_ops.py
# Adapter that your instruction_registry binds to (handlers must be (ctx, *args) style)
from typing import Any, Dict
from backend.modules.symbolic_engine import physics_kernel as PK
from backend.modules.symbolic_engine import quantum_kernel as QK
from backend.modules.symbolic_engine import gr_kernel as GR

# --- Vector/Tensor calculus (already wired by you) ---
def execute_grad(ctx, field, coords=None):         return PK.grad(field, coords).to_dict()
def execute_div(ctx, vec, coords=None):            return PK.div(vec, coords).to_dict()
def execute_curl(ctx, vec, coords=None):           return PK.curl(vec, coords).to_dict()
def execute_laplacian(ctx, field, coords=None):    return PK.laplacian(field, coords).to_dict()
def execute_d_dt(ctx, expr, t=None):               return PK.d_dt(expr, t or "t").to_dict()
def execute_dot(ctx, A, B):                        return PK.dot(A, B).to_dict()
def execute_cross(ctx, A, B):                      return PK.cross(A, B).to_dict()
def execute_tensor_product(ctx, A, B):             return PK.tensor_product(A, B).to_dict()

# --- Quantum stubs ---
def execute_schrodinger_step(ctx, psi, H, dt: float):   return QK.schrodinger_step(psi, H, float(dt)).to_dict()
def execute_apply_gate(ctx, state, gate: str, wires):   return QK.apply_gate(state, str(gate), wires).to_dict()
def execute_measure(ctx, state, wires, shots: int = 1024): return QK.measure(state, wires, int(shots)).to_dict()
def execute_entangle(ctx, state, pairs):                return QK.entangle(state, pairs).to_dict()

# --- GR stubs ---
def execute_riemann(ctx, metric):           return GR.riemann_curvature(metric).to_dict()
def execute_ricci_tensor(ctx, metric):      return GR.ricci_tensor(metric).to_dict()
def execute_ricci_scalar(ctx, metric):      return GR.ricci_scalar(metric).to_dict()
def execute_einstein(ctx, metric):          return GR.einstein_tensor(metric).to_dict()
def execute_geodesics(ctx, metric, coords): return GR.geodesic_equations(metric, coords).to_dict()