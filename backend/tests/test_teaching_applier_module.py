from __future__ import annotations

from pathlib import Path

from backend.modules.aion_conversation.minimal_response_composer import AionKnowledgeState
from backend.modules.aion_learning.teaching_applier import apply_teaching_to_ks
from backend.modules.aion_learning.teaching_memory_store import TeachingMemoryStore
from backend.modules.aion_learning.teaching_retriever import TeachingRetriever


def _mk_ks(confidence: float = 0.38) -> AionKnowledgeState:
    return AionKnowledgeState(
        intent="answer",
        topic="AION Phase 0 conversation",
        confidence=confidence,
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


def _seed_store(store: TeachingMemoryStore) -> None:
    store.clear()
    store.upsert_concept(
        concept_label="roadmap_explanation_simple",
        corrected_response=(
            "AION already has the core runtime online. Next, it is building conversation "
            "orchestration, skill runtime unification, and learning loops."
        ),
        target_confidence=0.72,
        tags=["phase0", "roadmap", "response-clarity"],
        notes="Lead with direct summary.",
        correction_reason="Too hesitant.",
        routing_hints={
            "intents": ["answer", "roadmap_explanation"],
            "topic_keywords": ["aion", "phase", "conversation", "roadmap", "building", "next"],
            "phrases": ["what aion is building next", "explain what aion is building next", "aion roadmap"],
        },
    )


def test_apply_teaching_to_ks_applies_for_roadmap_query(tmp_path: Path) -> None:
    store = TeachingMemoryStore(tmp_path / "phase0_learning_memory.json")
    _seed_store(store)

    ks = _mk_ks(0.38)
    meta = apply_teaching_to_ks(
        ks=ks,
        user_text="Explain what AION is building next.",
        store=store,
        retriever=TeachingRetriever(min_score=1.0),
    )

    assert meta["teaching_applied"] is True
    assert "roadmap_explanation_simple" in meta["applied_concepts"]
    assert meta["teaching_match_score"] >= 5.0
    assert ks.confidence == 0.62
    assert "Phase 0 conversation loop is stable and regression-tested" in ks.known_facts
    assert "apply teaching corrections to future responses" in ks.goals
    assert "response generation path" not in ks.unresolved


def test_apply_teaching_to_ks_no_match_leaves_ks_unchanged(tmp_path: Path) -> None:
    store = TeachingMemoryStore(tmp_path / "phase0_learning_memory.json")
    _seed_store(store)

    ks = _mk_ks(0.38)
    before = {
        "confidence": ks.confidence,
        "known_facts": list(ks.known_facts),
        "goals": list(ks.goals),
        "unresolved": list(ks.unresolved),
    }

    meta = apply_teaching_to_ks(
        ks=ks,
        user_text="Write me a poem about the sea.",
        store=store,
        retriever=TeachingRetriever(min_score=1.0),
    )

    assert meta["teaching_applied"] is False
    assert meta["applied_concepts"] == []
    assert ks.confidence == before["confidence"]
    assert ks.known_facts == before["known_facts"]
    assert ks.goals == before["goals"]
    assert ks.unresolved == before["unresolved"]


def test_apply_teaching_to_ks_preserves_high_confidence(tmp_path: Path) -> None:
    store = TeachingMemoryStore(tmp_path / "phase0_learning_memory.json")
    _seed_store(store)

    ks = _mk_ks(0.93)
    meta = apply_teaching_to_ks(
        ks=ks,
        user_text="Explain what AION is building next.",
        store=store,
        retriever=TeachingRetriever(min_score=1.0),
    )

    assert meta["teaching_applied"] is True
    assert ks.confidence >= 0.90
    assert ks.confidence == 0.93  # monotonic + no reduction to target=0.72