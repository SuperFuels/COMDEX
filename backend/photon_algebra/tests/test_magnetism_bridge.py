from __future__ import annotations

from backend.photon_algebra.magnetism_bridge import (
    MagneticIntent,
    PhotonFieldIntent,
    PhotonMagnetismBridge,
)


def test_compile_expr_superposition_produces_distributed_interference_intent():
    bridge = PhotonMagnetismBridge()

    expr = {"op": "⊕", "states": ["a", "b"]}
    intent = bridge.compile_expr(expr)

    assert isinstance(intent, PhotonFieldIntent)
    assert intent.semantic_label == "superposed_field"
    assert intent.symbol_hint is None

    mi = intent.magnetic_intent
    assert isinstance(mi, MagneticIntent)
    assert mi.mode == "distributed_interference"
    assert mi.coherence_target == 0.5
    assert mi.rotational_memory_target == 0.4
    assert mi.coupling_target == 0.0
    assert mi.containment_target == 0.0


def test_compile_expr_fusion_produces_constructive_lock_intent():
    bridge = PhotonMagnetismBridge()

    expr = {"op": "⊗", "states": ["a", "b"]}
    intent = bridge.compile_expr(expr)

    assert intent.semantic_label == "fused_field"
    assert intent.symbol_hint == "S1"

    mi = intent.magnetic_intent
    assert mi.mode == "constructive_lock"
    assert mi.coherence_target == 0.7
    assert mi.rotational_memory_target == 0.6
    assert mi.containment_target == 0.7
    assert mi.coupling_target == 0.0


def test_compile_expr_entanglement_produces_coupled_alignment_intent():
    bridge = PhotonMagnetismBridge()

    expr = {"op": "↔", "states": ["a", "b"]}
    intent = bridge.compile_expr(expr)

    assert intent.semantic_label == "entangled_alignment"
    assert intent.symbol_hint == "S2"

    mi = intent.magnetic_intent
    assert mi.mode == "coupled_alignment"
    assert mi.coherence_target == 0.8
    assert mi.rotational_memory_target == 0.7
    assert mi.coupling_target == 0.9
    assert mi.containment_target == 0.0


def test_compile_expr_phi_b_produces_magnetic_state_intent():
    bridge = PhotonMagnetismBridge()

    expr = {"op": "Φ_B", "state": "a"}
    intent = bridge.compile_expr(expr)

    assert isinstance(intent, PhotonFieldIntent)
    assert intent.semantic_label == "magnetic_state_field"
    assert intent.symbol_hint == "S2"

    mi = intent.magnetic_intent
    assert isinstance(mi, MagneticIntent)
    assert mi.mode == "magnetic_state_encoding"
    assert mi.coherence_target == 0.75
    assert mi.rotational_memory_target == 0.9
    assert mi.coupling_target == 0.6
    assert mi.containment_target == 0.3


def test_compile_expr_magnetic_product_produces_magnetic_coupling_intent():
    bridge = PhotonMagnetismBridge()

    expr = {"op": "⊗_M", "states": ["a", "b"]}
    intent = bridge.compile_expr(expr)

    assert isinstance(intent, PhotonFieldIntent)
    assert intent.semantic_label == "magnetically_coupled_field"
    assert intent.symbol_hint == "S2"

    mi = intent.magnetic_intent
    assert isinstance(mi, MagneticIntent)
    assert mi.mode == "magnetic_coupling"
    assert mi.coherence_target == 0.8
    assert mi.rotational_memory_target == 0.85
    assert mi.coupling_target == 0.95
    assert mi.containment_target == 0.4


def test_compile_expr_normalizes_before_assigning_intent():
    bridge = PhotonMagnetismBridge()

    expr = {
        "op": "⊕",
        "states": [
            "a",
            {"op": "⊗", "states": ["a", "b"]},
        ],
    }
    intent = bridge.compile_expr(expr)

    assert intent.normalized_expr == "a"
    assert intent.semantic_label == "unknown"
    assert intent.magnetic_intent.mode == "passive"


def test_compile_to_symatics_program_uses_fallback_symbol_and_attaches_metadata():
    bridge = PhotonMagnetismBridge(
        "backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs/symatics_symbol_reference_catalog.json"
    )

    expr = {"op": "↔", "states": ["a", "b"]}
    intent, program = bridge.compile_to_symatics_program(
        expr,
        fallback_symbol_id="S2",
        amplitude=1.25,
        frequency=0.75,
    )

    assert intent.semantic_label == "entangled_alignment"

    assert program.symbol_id == "S2"
    assert program.amplitude == 1.25
    assert program.frequency == 0.75

    md = program.metadata
    assert md["source"] == "PhotonMagnetismBridge"
    assert md["semantic_label"] == "entangled_alignment"
    assert md["magnetic_mode"] == "coupled_alignment"
    assert md["coherence_target"] == 0.8
    assert md["rotational_memory_target"] == 0.7
    assert md["coupling_target"] == 0.9
    assert md["containment_target"] == 0.0


def test_compile_to_symatics_program_phi_b_uses_hint_and_attaches_metadata():
    bridge = PhotonMagnetismBridge(
        "backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs/symatics_symbol_reference_catalog.json"
    )

    expr = {"op": "Φ_B", "state": "a"}
    intent, program = bridge.compile_to_symatics_program(
        expr,
        fallback_symbol_id="S1",
        amplitude=1.0,
        frequency=1.0,
    )

    assert intent.semantic_label == "magnetic_state_field"
    assert intent.symbol_hint == "S2"

    assert program.symbol_id == "S2"

    md = program.metadata
    assert md["source"] == "PhotonMagnetismBridge"
    assert md["semantic_label"] == "magnetic_state_field"
    assert md["magnetic_mode"] == "magnetic_state_encoding"
    assert md["coherence_target"] == 0.75
    assert md["rotational_memory_target"] == 0.9
    assert md["coupling_target"] == 0.6
    assert md["containment_target"] == 0.3


def test_compile_to_symatics_program_magnetic_product_uses_hint_and_attaches_metadata():
    bridge = PhotonMagnetismBridge(
        "backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs/symatics_symbol_reference_catalog.json"
    )

    expr = {"op": "⊗_M", "states": ["a", "b"]}
    intent, program = bridge.compile_to_symatics_program(
        expr,
        fallback_symbol_id="S1",
        amplitude=1.0,
        frequency=1.0,
    )

    assert intent.semantic_label == "magnetically_coupled_field"
    assert intent.symbol_hint == "S2"

    assert program.symbol_id == "S2"

    md = program.metadata
    assert md["source"] == "PhotonMagnetismBridge"
    assert md["semantic_label"] == "magnetically_coupled_field"
    assert md["magnetic_mode"] == "magnetic_coupling"
    assert md["coherence_target"] == 0.8
    assert md["rotational_memory_target"] == 0.85
    assert md["coupling_target"] == 0.95
    assert md["containment_target"] == 0.4


def test_compile_to_symatics_program_without_compiler_raises():
    bridge = PhotonMagnetismBridge()

    expr = {"op": "⊕", "states": ["a", "b"]}

    try:
        bridge.compile_to_symatics_program(expr)
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "SymaticsFieldCompiler not configured" in str(exc)