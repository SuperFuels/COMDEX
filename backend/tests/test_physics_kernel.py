# backend/tests/test_physics_kernel.py
from backend.modules.symbolic_engine.physics_kernel import (
    grad, div, curl, laplacian, d_dt, tensor_product, dot, cross,
    ket, operator, hamiltonian, commutator, schrodinger_evolution,
    metric, covariant_derivative, einstein_tensor, einstein_equation,
    GlyphNode
)

def node(x): return x.to_dict() if isinstance(x, GlyphNode) else x

def test_vector_calculus_nodes():
    f = "φ(x,y,z)"
    V = {"type":"Vector","name":"V","components":["Vx","Vy","Vz"]}
    assert node(grad(f))["op"] == "∇"
    assert node(div(V))["op"] == "∇*"
    assert node(curl(V))["op"] == "∇*"
    assert node(laplacian(f))["op"] == "∇2"
    assert node(d_dt(f))["op"] == "∂/∂t"
    assert node(tensor_product("A","B"))["op"] == "⊗"
    assert node(dot("A","B"))["op"] == "*"
    assert node(cross("A","B"))["op"] == "*"

def test_quantum_nodes():
    ψ = ket("ψ")
    H = hamiltonian()
    assert node(commutator(operator("X"), operator("P")))["op"] == "[ , ]"
    eq = node(schrodinger_evolution(ψ, H))
    assert eq["meta"]["equation"] == "Schr"

def test_gr_nodes():
    g = metric()
    G = einstein_tensor()
    T = {"type":"Tensor","name":"T_{μν}"}
    eq = einstein_equation(G, T).to_dict()
    assert eq["meta"]["equation"] == "Einstein"
    assert eq["op"] == "≐"