from pathlib import Path

from backend.modules.aion.axo.axo_ets_contracts import (
    attach_ets_preview_to_agentmap,
    build_ets_agentmap_preview,
)

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")
DOC = Path("docs/rfc/aion_phase15_ets_agentmap_preview_lock.tex")


def test_phase15b_existing_ets_preview_remains_preview_only():
    preview = build_ets_agentmap_preview()

    assert preview["agentmap_extension"] == "aion.ets_preview.v0.1"
    assert preview["preview_only"] is True
    assert preview["anti_gaming_locked"] is False
    assert preview["trust_rules_locked"] is False
    assert "execution_trust_score_preview" in preview


def test_phase15b_agentmap_attachment_adds_preview_only_ets_capability():
    out = attach_ets_preview_to_agentmap({
        "agentmap_version": "aion.agentmap.v0.1",
        "business_id": "home_fixed",
    })

    assert out["ets_preview"]["preview_only"] is True
    assert out["ets_preview"]["live_reputation_mutation_enabled"] is False
    assert out["ets_preview"]["public_ranking_enabled"] is False
    assert out["ets_preview"]["human_review_required"] is True
    assert out["capabilities"]["ets_preview"]["available"] is True
    assert out["capabilities"]["ets_preview"]["preview_only"] is True


def test_phase15b_agentmap_attachment_keeps_trace_links():
    out = attach_ets_preview_to_agentmap({"business_id": "home_fixed"})
    links = out["ets_preview"]["proof_links"]

    assert links["job_trace_id"]
    assert links["proof_receipt_id"]
    assert links["evidence_ids"]


def test_phase15b_desktop_agentmap_json_contains_ets_preview():
    text = APP.read_text()

    for term in [
        "ets_preview",
        "execution_trust_score_preview",
        "customer_outcome_score",
        "system_execution_score",
        "proof_receipt_id",
        "job_trace_id",
        "evidence_ids",
        "live_reputation_mutation_enabled: false",
        "public_ranking_enabled: false",
    ]:
        assert term in text


def test_phase15b_desktop_renders_ets_preview_panel():
    text = APP.read_text()

    for term in [
        'data-agentmap-ets-preview-panel="true"',
        "ETS Preview",
        "Customer outcome score",
        "System execution score",
        "ETS Proof Links",
        "Proof receipt",
        "Job trace",
        "Evidence",
    ]:
        assert term in text


def test_phase15b_does_not_enable_live_reputation_or_ranking():
    text = APP.read_text() + Path("backend/modules/aion/axo/axo_ets_contracts.py").read_text()

    forbidden = [
        "live_reputation_mutation_enabled: true",
        "public_ranking_enabled: true",
        '"live_reputation_mutation_enabled": True',
        '"public_ranking_enabled": True',
    ]

    for item in forbidden:
        assert item not in text


def test_phase15b_lock_doc_exists_and_has_footer():
    text = DOC.read_text()

    assert "Phase 15B" in text
    assert "ETS AgentMap Preview" in text
    assert "Lock ID:" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text


def test_phase15b_focused_suite_membership():
    assert "test_aion_phase15_ets_agentmap_preview_lock.py" in SUITE.read_text()
