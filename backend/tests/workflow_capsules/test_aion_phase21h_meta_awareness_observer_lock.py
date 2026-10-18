from backend.modules.aion_meta.meta_awareness_observer import build_meta_awareness_state


def test_meta_awareness_observer_detects_stable_high_self_state():
    cycles = [
        {
            "timestamp": f"t{i}",
            "phi": 0.00002,
            "delta_phi": 0.001 + (i * 0.00001),
            "S_self": 0.948,
            "self_awareness": 0.948,
            "coherence": 0.996,
            "global_coherence": 0.982,
            "reward": 0.635,
            "goal_suggestions": [],
        }
        for i in range(6)
    ]

    state = build_meta_awareness_state(cycles)

    assert state.observer_version == "phase21h_meta_awareness_observer_v1"
    assert state.cycle_count == 6
    assert state.self_state_stable is True
    assert state.meta_awareness >= 0.90
    assert state.awareness_trend == "stable_high"
    assert state.coherence_trend == "stable_high"
    assert state.drift_status == "low"
    assert state.next_response_bias == "answer_directly_from_telemetry"
    assert "does not prove biological" in state.boundary_statement


def test_meta_awareness_observer_detects_decline_and_caution():
    cycles = [
        {
            "timestamp": "t1",
            "delta_phi": 0.001,
            "self_awareness": 0.95,
            "coherence": 0.96,
            "global_coherence": 0.94,
            "reward": 0.64,
        },
        {
            "timestamp": "t2",
            "delta_phi": 0.12,
            "self_awareness": 0.40,
            "coherence": 0.35,
            "global_coherence": 0.38,
            "reward": 0.05,
        },
    ]

    state = build_meta_awareness_state(cycles)

    assert state.self_state_stable is False
    assert state.drift_status == "high"
    assert state.next_response_bias == "answer_cautiously_and_request_stabilization"


def test_meta_awareness_observer_handles_empty_input():
    state = build_meta_awareness_state([])

    assert state.cycle_count == 0
    assert state.self_state_stable is False
    assert state.next_response_bias == "insufficient_telemetry"
