from __future__ import annotations

from backend.modules.aion_fabric.live_news import LiveNewsIntelligence


def test_live_news_compiles_claims_sources_corrections_and_privacy(tmp_path):
    intelligence = LiveNewsIntelligence(tmp_path)
    result = intelligence.compile(
        live_context={
            "recent_statement": "The programme says inflation fell to two percent this month.",
            "created_at": "2026-08-29T12:00:00+00:00",
        },
        research={
            "provider": "openai_responses_web_search",
            "created_at": "2026-08-29T12:00:05+00:00",
            "answer": "Misleading: the figure uses a different measurement period.",
            "verdict": "Misleading",
            "confidence": 0.82,
            "context_notes": ["Monthly and annual rates are not interchangeable."],
            "items": [
                {
                    "title": "Official statistics",
                    "url": "https://statistics.example.gov/release",
                    "reason": "Primary release",
                },
                {
                    "title": "Unsafe device page",
                    "url": "http://192.168.1.1/admin",
                    "reason": "Must be excluded",
                },
            ],
            "claims": [
                {
                    "claim": "Inflation fell to two percent.",
                    "verdict": "Misleading",
                    "explanation": "The two-percent figure is monthly rather than annual.",
                    "confidence": 0.82,
                    "source_indexes": [1, 2, 99],
                    "date_scope": "August 2026",
                }
            ],
        },
        screen_understanding={
            "corrections": [
                {
                    "field": "subtitle",
                    "value": "The presenter said two percent month-on-month.",
                    "created_at": "2026-08-29T12:00:02+00:00",
                }
            ]
        },
        latency_ms=842,
    )

    assert result["verdict"] == "Misleading"
    assert result["claims"][0]["source_indexes"] == [1]
    assert result["sources"][0]["source_class"] == "government_or_intergovernmental"
    assert len(result["sources"]) == 1
    assert [item["event"] for item in result["correction_timeline"]] == [
        "statement_captured",
        "owner_correction",
        "evidence_researched",
    ]
    assert result["presentation"]["spoken_summary_preserves_playback"] is True
    assert result["presentation"]["third_party_tv_overlay_supported"] is False
    assert result["privacy"]["raw_audio_retained"] is False
    assert result["privacy"]["source_pixels_retained"] is False
    assert result["schema_version"] == "pilot.live-news.v2"
    assert result["sources"][0]["quality_score"] == 0.95
    assert result["performance"] == {
        "latency_ms": 842,
        "source_count": 1,
        "mean_source_quality": 0.95,
        "quality_measured_outside_model": True,
    }
    assert result["contradiction_analysis"]["model_cannot_create_source_disagreement"] is True
    assert result["evidence_hash"]
    assert intelligence.latest()["fact_check_id"] == result["fact_check_id"]
    assert intelligence.history()[0]["verdict"] == "Misleading"


def test_live_news_handoff_is_explicitly_unverifiable(tmp_path):
    result = LiveNewsIntelligence(tmp_path).compile(
        live_context={"recent_statement": "An unsupported current claim."},
        research={
            "provider": "safe_search_handoff",
            "answer": "Open current sources to verify this claim.",
            "verdict": "Supported",
            "confidence": 1,
            "items": [{"title": "Search", "url": "https://www.google.com/search?q=claim"}],
        },
    )

    assert result["verdict"] == "Unverifiable"
    assert result["confidence"] == 0
    assert result["evidence_status"] == "insufficient_or_handoff"


def test_live_news_followups_are_derived_from_frozen_evidence(tmp_path):
    intelligence = LiveNewsIntelligence(tmp_path)
    intelligence.compile(
        live_context={"recent_statement": "The rate was two percent."},
        research={
            "provider": "public_evidence",
            "answer": "The figure needs its measurement period.",
            "verdict": "Misleading",
            "confidence": 0.8,
            "context_notes": ["Monthly and annual rates answer different questions."],
            "items": [
                {"title": "Editorial report", "url": "https://news.example/report"},
                {"title": "Primary statistics", "url": "https://data.example.gov/release"},
            ],
            "claims": [
                {"claim": "The rate was two percent.", "verdict": "Misleading", "date_scope": "August 2026", "source_indexes": [1, 2]},
                {"claim": "The annual rate was two percent.", "verdict": "False", "date_scope": "Year to August 2026", "source_indexes": [2]},
            ],
        },
    )

    evidence = intelligence.follow_up("evidence")
    disagreement = intelligence.follow_up("disagreement")
    difference = intelligence.follow_up("difference")

    assert evidence["derived_without_model"] is True
    assert "Primary statistics" in evidence["answer"]
    assert evidence["playback_preserved"] is True
    assert "will not invent" in disagreement["answer"]
    assert "different dates or measurement periods" in difference["answer"]
    assert evidence["fact_check_id"] == difference["fact_check_id"]


def test_live_news_detects_conflicting_verdicts_for_same_claim(tmp_path):
    result = LiveNewsIntelligence(tmp_path).compile(
        live_context={"recent_statement": "The event starts today."},
        research={
            "provider": "public_evidence",
            "answer": "Sources conflict.",
            "verdict": "Disputed",
            "confidence": 0.6,
            "items": [{"title": "Event source", "url": "https://event.example/schedule"}],
            "claims": [
                {"claim": "The event starts today", "verdict": "Supported", "source_indexes": [1]},
                {"claim": "The event starts today!", "verdict": "False", "source_indexes": [1]},
            ],
        },
    )

    assert result["contradiction_analysis"]["contradictions_detected"] == 1
