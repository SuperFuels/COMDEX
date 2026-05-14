from __future__ import annotations

import json
from pathlib import Path

import backend.scripts.test_phase01_learning_loop as harness
from backend.modules.aion_conversation.minimal_response_composer import AionKnowledgeState


def _base_ks() -> AionKnowledgeState:
    return AionKnowledgeState(
        intent="answer",
        topic="AION Phase 0 conversation",
        confidence=0.38,
        known_facts=[
            "AION runtime modules are already active through launch_tessaris_stack.sh",
            "TCFK fusion provides live coherence telemetry",
        ],
        goals=[
            "build a stable conversation loop",
            "store teacher corrections in structured schema",
        ],
        unresolved=[
            "response generation path",
            "teaching session format",
        ],
        fusion_snapshot={"sigma": 0.81, "psi_tilde": 0.74},
        source_refs=["TCFK", "RAL", "Theta Orchestrator"],
    )


def _write_memory(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "concepts": {
                    "roadmap_explanation_simple": {
                        "concept_label": "roadmap_explanation_simple",
                        "corrected_response": "AION already has the core runtime online. Next it is building the stronger conversation layer.",
                        "target_confidence": 0.72,
                        "tags": ["phase0", "roadmap", "response-clarity"],
                        "notes": "Lead with direct summary sentence.",
                        "correction_reason": "Too hesitant",
                        "routing_hints": {
                            "intents": ["answer", "roadmap_explanation"],
                            "topic_keywords": ["aion", "phase", "conversation", "roadmap", "building", "next"],
                            "phrases": ["what aion is building next", "explain what aion is building next"],
                        },
                    }
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_apply_teaching_to_ks_applies_match(tmp_path, monkeypatch):
    memfile = tmp_path / "phase0_learning_memory.json"
    _write_memory(memfile)

    monkeypatch.setattr(harness, "TEACHING_MEMORY_FILE", memfile)

    ks = _base_ks()
    meta = harness._apply_teaching_to_ks(ks, "Explain what AION is building next.")

    assert meta["teaching_applied"] is True
    assert "roadmap_explanation_simple" in meta.get("applied_concepts", [])
    assert float(meta.get("teaching_match_score", 0.0)) > 0.0
    assert isinstance(meta.get("teaching_match_reasons", []), list)

    # Confidence uplift
    assert ks.confidence > 0.38
    assert ks.confidence <= 0.95

    # Unresolved reduced / reshaped
    assert "response generation path" not in ks.unresolved
    assert "teaching session format" not in ks.unresolved
    assert len(ks.unresolved) >= 1

    # Facts/goals strengthened
    assert any("regression-tested" in f for f in ks.known_facts)
    assert any("apply teaching corrections" in g for g in ks.goals)


def test_apply_teaching_to_ks_no_match_leaves_ks_unchanged(tmp_path, monkeypatch):
    memfile = tmp_path / "phase0_learning_memory.json"
    _write_memory(memfile)

    monkeypatch.setattr(harness, "TEACHING_MEMORY_FILE", memfile)

    ks = _base_ks()
    before = {
        "confidence": ks.confidence,
        "known_facts": list(ks.known_facts),
        "goals": list(ks.goals),
        "unresolved": list(ks.unresolved),
    }

    meta = harness._apply_teaching_to_ks(ks, "Write me a poem about the sea.")

    assert meta["teaching_applied"] is False
    assert meta.get("applied_concepts", []) == []

    assert ks.confidence == before["confidence"]
    assert list(ks.known_facts) == before["known_facts"]
    assert list(ks.goals) == before["goals"]
    assert list(ks.unresolved) == before["unresolved"]


def test_apply_teaching_to_ks_bounds_confidence(tmp_path, monkeypatch):
    memfile = tmp_path / "phase0_learning_memory.json"
    _write_memory(memfile)

    monkeypatch.setattr(harness, "TEACHING_MEMORY_FILE", memfile)

    ks = _base_ks()
    ks.confidence = 0.90  # already high
    meta = harness._apply_teaching_to_ks(ks, "Explain what AION is building next.")

    assert meta["teaching_applied"] is True
    assert ks.confidence <= 0.95
    # target in memory is 0.72, so logic should not reduce confidence
    assert ks.confidence >= 0.90