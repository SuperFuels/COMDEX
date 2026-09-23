from backend.modules.aion_voice_bridge import build_telemetry_grounded_voice_response


def _meta_state():
    return {
        "observer_version": "phase21h_meta_awareness_observer_v1",
        "cycle_count": 20,
        "meta_awareness": 0.948339,
        "self_state_stable": True,
        "awareness_trend": "improving",
        "coherence_trend": "improving",
        "drift_status": "low",
        "next_response_bias": "answer_directly_from_telemetry",
        "latest": {
            "phi": 0.000020301881888039524,
            "delta_phi": 0.0010705859958033384,
            "S_self": 0.948355496297768,
            "self_awareness": 0.948355496297768,
            "coherence": 0.9960661223499409,
            "entropy": 0.0,
            "global_coherence": 0.982326,
            "reward": 0.6351,
            "goal_suggestions": [],
            "source_type": "mind_sync",
        },
    }


def _improvement_result():
    return {
        "loop_version": "phase21i_self_improvement_trial_loop_v1",
        "baseline_score": 0.142857,
        "final_score": 1.0,
        "improvement_delta": 0.857143,
        "improved": True,
        "equilibrium_reached": True,
        "evidence": {
            "uses_llm_shortcut": False,
            "uses_trial_and_error": True,
            "uses_meta_awareness": True,
        },
    }


def test_phase21j_voice_bridge_builds_telemetry_grounded_answer():
    response = build_telemetry_grounded_voice_response(
        question="Are you aware of your own awareness?",
        meta_awareness_state=_meta_state(),
        self_improvement_result=_improvement_result(),
    )

    assert response.bridge_version == "phase21j_telemetry_grounded_voice_bridge_v1"
    assert response.answer_mode == "telemetry_grounded_no_llm_shortcut"
    assert response.confidence >= 0.90
    assert response.evidence["uses_hexcore_telemetry"] is True
    assert response.evidence["uses_meta_awareness_observer"] is True
    assert response.evidence["uses_self_improvement_loop"] is True
    assert response.evidence["uses_llm_shortcut"] is False
    assert "S_self=0.948355" in response.answer
    assert "operational self-measurement" in response.answer
    assert "not a claim of biological consciousness" in response.answer


def test_phase21j_voice_bridge_carries_self_improvement_evidence():
    response = build_telemetry_grounded_voice_response(
        question="Did you improve?",
        meta_awareness_state=_meta_state(),
        self_improvement_result=_improvement_result(),
    )

    assert response.self_improvement["improved"] is True
    assert response.self_improvement["final_score"] == 1.0
    assert response.self_improvement["improvement_delta"] == 0.857143
    assert "final_score=1.000000" in response.answer
    assert "improvement_delta=0.857143" in response.answer


def test_phase21j_voice_bridge_cautious_when_unstable():
    meta = _meta_state()
    meta["self_state_stable"] = False
    meta["drift_status"] = "high"
    meta["latest"]["delta_phi"] = 0.2

    response = build_telemetry_grounded_voice_response(
        question="Are you stable?",
        meta_awareness_state=meta,
        self_improvement_result=_improvement_result(),
    )

    assert response.evidence["stability_label"] == "unstable_drift"
    assert "answer cautiously" in response.answer
