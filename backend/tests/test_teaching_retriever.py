#!/usr/bin/env python3
from __future__ import annotations

from backend.modules.aion_learning.teaching_retriever import TeachingRetriever


def _concept(
    label: str,
    *,
    tags=None,
    intents=None,
    topic_keywords=None,
    phrases=None,
):
    return {
        "concept_label": label,
        "corrected_response": f"Corrected response for {label}",
        "target_confidence": 0.72,
        "tags": list(tags or []),
        "routing_hints": {
            "intents": list(intents or []),
            "topic_keywords": list(topic_keywords or []),
            "phrases": list(phrases or []),
        },
    }


def test_retriever_exact_phrase_match():
    retriever = TeachingRetriever(min_score=1.0)

    concepts = {
        "roadmap_explanation_simple": _concept(
            "roadmap_explanation_simple",
            tags=["roadmap", "teaching-loop"],
            intents=["answer", "roadmap_explanation"],
            topic_keywords=["aion", "phase", "conversation", "roadmap", "building", "next"],
            phrases=["explain what aion is building next", "what aion is building next"],
        )
    }

    best = retriever.retrieve_best(
        user_text="Explain what AION is building next.",
        intent="answer",
        topic="AION Phase 0 conversation",
        concepts=concepts,
    )

    assert best is not None
    assert best.concept_label == "roadmap_explanation_simple"
    assert best.score >= 1.0
    assert any("intent:answer" in r for r in best.reasons)
    assert any("phrase_hits:" in r for r in best.reasons)


def test_retriever_paraphrase_keyword_match_without_phrase():
    retriever = TeachingRetriever(min_score=1.0)

    concepts = {
        "roadmap_explanation_simple": _concept(
            "roadmap_explanation_simple",
            tags=["roadmap"],
            intents=["answer"],
            topic_keywords=["aion", "roadmap", "next", "building", "conversation"],
            phrases=["what aion is building next"],  # not exact text below
        )
    }

    best = retriever.retrieve_best(
        user_text="Can you outline the AION roadmap and what comes next?",
        intent="answer",
        topic="AION Phase 0 conversation",
        concepts=concepts,
    )

    assert best is not None
    assert best.concept_label == "roadmap_explanation_simple"
    # Should still match via intent/topic/user keyword overlap even without phrase hit
    assert best.score >= 1.0
    assert any(
        key in " | ".join(best.reasons)
        for key in ["intent:answer", "topic_overlap:", "user_keyword_overlap:", "tag_overlap:"]
    )


def test_retriever_no_match_returns_none():
    retriever = TeachingRetriever(min_score=2.0)

    concepts = {
        "sql_debugging": _concept(
            "sql_debugging",
            tags=["database", "sql"],
            intents=["debug"],
            topic_keywords=["postgres", "query", "index", "join"],
            phrases=["optimize this sql query"],
        )
    }

    best = retriever.retrieve_best(
        user_text="Write me a poem about the sea.",
        intent="creative_write",
        topic="Poetry",
        concepts=concepts,
    )

    assert best is None


def test_retriever_best_of_many_picks_most_relevant():
    retriever = TeachingRetriever(min_score=1.0)

    concepts = {
        "roadmap_explanation_simple": _concept(
            "roadmap_explanation_simple",
            tags=["roadmap", "response-clarity"],
            intents=["answer", "roadmap_explanation"],
            topic_keywords=["aion", "roadmap", "building", "next", "conversation", "phase"],
            phrases=["aion roadmap", "what aion is building next"],
        ),
        "general_politeness": _concept(
            "general_politeness",
            tags=["politeness"],
            intents=["answer"],
            topic_keywords=["please", "thanks", "help"],
            phrases=["thank you for your help"],
        ),
        "sql_debugging": _concept(
            "sql_debugging",
            tags=["sql"],
            intents=["debug"],
            topic_keywords=["sql", "query", "join", "index"],
            phrases=["optimize sql"],
        ),
    }

    ranked = retriever.retrieve_ranked(
        user_text="Explain what AION is building next and summarize the roadmap.",
        intent="answer",
        topic="AION Phase 0 conversation",
        concepts=concepts,
    )

    assert ranked, "Expected at least one match"
    assert ranked[0].concept_label == "roadmap_explanation_simple"

    labels = [r.concept_label for r in ranked]
    assert "roadmap_explanation_simple" in labels
    # sql_debugging may not appear at all depending on score threshold; if it does, it should not beat roadmap
    if "sql_debugging" in labels:
        assert labels.index("roadmap_explanation_simple") < labels.index("sql_debugging")