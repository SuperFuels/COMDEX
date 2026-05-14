import json
import pytest
from backend.modules.glyphwave.entanglement.entanglement_engine import EntanglementEngine


@pytest.fixture
def engine():
    """Fresh EntanglementEngine for each test."""
    return EntanglementEngine()


def make_wave(id_suffix, phi, coherence):
    """Helper to create a synthetic wave object."""
    return {
        "id": f"wave_{id_suffix}",
        "field_potential": phi,
        "coherence": coherence,
        "amplitude": phi * 0.5,
        "phase": phi * 0.1,
    }


def test_entangle_creates_edge_with_expected_fields(engine):
    wave_a = make_wave("A", 1.2, 0.95)
    wave_b = make_wave("B", 0.9, 0.9)

    eid = engine.entangle(wave_a, wave_b)
    assert isinstance(eid, str)
    edges = list(engine.graph.edges(data=True))
    assert len(edges) == 1

    (_, _, data) = edges[0]
    assert data["entanglement_id"] == eid
    assert "field_potential" in data
    assert "coherence" in data
    assert "entropy_shift" in data
    assert data["coherence"] <= 1.0
    assert data["entropy_shift"] > 0.0


def test_coherence_and_entropy_relationships(engine):
    w1 = make_wave("X", 1.0, 0.95)
    w2 = make_wave("Y", 2.0, 0.95)

    eid = engine.entangle(w1, w2)
    data = list(engine.graph.edges(data=True))[0][2]

    # ΔS grows with field potential difference
    delta_s = abs(w1["field_potential"] - w2["field_potential"]) * 0.01
    assert pytest.approx(data["entropy_shift"], rel=1e-3) == delta_s

    # Coherence must decay as ΔS increases
    assert data["coherence"] < 0.95


def test_collapse_all_removes_low_coherence_edges(engine):
    # One high-coherence and one low-coherence entanglement
    w1 = make_wave("A1", 1.0, 0.9)
    w2 = make_wave("A2", 1.0, 0.9)
    w3 = make_wave("B1", 1.0, 0.1)
    w4 = make_wave("B2", 1.0, 0.1)

    eid_high = engine.entangle(w1, w2)
    eid_low = engine.entangle(w3, w4)
    assert len(engine.graph.edges) == 2

    metrics = engine.collapse_all(C_MIN=0.2)
    remaining = len(engine.graph.edges)

    assert "collapsed_edges" in metrics
    assert metrics["collapsed_edges"] >= 1
    assert remaining < 2


def test_export_graph_serialization(engine):
    w1 = make_wave("G1", 1.0, 0.8)
    w2 = make_wave("G2", 0.8, 0.85)
    engine.entangle(w1, w2)

    json_str = engine.export_graph()
    data = json.loads(json_str)
    assert "nodes" in data and "links" in data
    assert len(data["links"]) >= 1