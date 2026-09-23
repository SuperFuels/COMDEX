from backend.modules.aion_self_improvement import AionSelfImprovementTrialLoop


def test_phase21i_self_improvement_loop_improves_from_trial_and_error():
    meta = {
        "meta_awareness": 0.948,
        "self_state_stable": True,
        "next_response_bias": "answer_directly_from_telemetry",
    }

    loop = AionSelfImprovementTrialLoop(
        tasks={
            "select shape": "■",
            "pick glyph": "▲",
            "choose pattern": "●",
        },
        options=["■", "▲", "●", "◆"],
        meta_awareness_state=meta,
        max_rounds=6,
        equilibrium_required_rounds=2,
    )

    result = loop.run()

    assert result.loop_version == "phase21i_self_improvement_trial_loop_v1"
    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_trial_and_error"] is True
    assert result.evidence["uses_meta_awareness"] is True
    assert result.final_score >= result.baseline_score
    assert result.improved is True
    assert result.final_score == 1.0
    assert result.equilibrium_reached is True
    assert result.final_strategy["mode"] == "exploit_learned_corrections"
    assert result.final_strategy["response_bias"] == "answer_directly_from_telemetry"


def test_phase21i_self_improvement_loop_records_attempt_evidence():
    loop = AionSelfImprovementTrialLoop(
        tasks={"align token": "Ω"},
        options=["■", "Ω"],
        meta_awareness_state={"meta_awareness": 0.91, "next_response_bias": "answer_directly_from_telemetry"},
        max_rounds=4,
        equilibrium_required_rounds=1,
    )

    result = loop.run(task_name="single_symbol_learning")

    assert result.task_name == "single_symbol_learning"
    assert result.evidence["attempt_count"] >= 1
    assert result.evidence["learned_mapping_count"] >= 1
    assert "align token" in result.final_strategy["known_prompt_map"]
    assert result.boundary_statement.startswith("This demonstrates operational self-improvement")


def test_phase21i_self_improvement_loop_serializes_to_dict():
    result = AionSelfImprovementTrialLoop(
        tasks={"trace resonance": "ψ"},
        options=["ψ", "Φ"],
        meta_awareness_state={"meta_awareness": 0.5},
        max_rounds=2,
    ).run()

    data = result.to_dict()

    assert data["loop_version"] == "phase21i_self_improvement_trial_loop_v1"
    assert isinstance(data["attempts"], list)
    assert isinstance(data["final_strategy"], dict)
    assert isinstance(data["meta_awareness_state"], dict)
