# /workspaces/COMDEX/backend/tests/test_aion_equities_openai_document_analysis_runtime.py
from __future__ import annotations

from backend.modules.aion_equities.openai_document_analysis_runtime import (
    OpenAIDocumentAnalysisRuntime,
)
from backend.modules.aion_equities.openai_operating_brief_store import (
    OpenAIOperatingBriefStore,
)


def _mock_openai_client(packet: dict) -> dict:
    return {
        "company_profile": {
            "company_ref": packet["company_ref"],
            "name": "Unilever PLC",
            "sector": "consumer_staples",
            "country": "GB",
        },
        "quarter_summary": {
            "document_ref": packet["document_ref"],
            "headline": "Stable demand with margin improvement.",
        },
        "trigger_map": {
            "triggers": [
                {"id": "fx_watch", "metric": "eur_gbp", "direction": "watch"},
            ]
        },
        "feed_candidates": {
            "feeds": ["consensus_estimates", "fx_rates"],
        },
    }


def test_openai_document_analysis_runtime_builds_packet_and_returns_response(tmp_path):
    brief_store = OpenAIOperatingBriefStore(tmp_path)
    brief_store.save_operating_brief(
        brief_id="brief/aion/v1",
        version="v1",
        title="AION Operating Brief",
        content="System brief for document analysis.",
        generated_by="pytest",
    )

    runtime = OpenAIDocumentAnalysisRuntime(
        operating_brief_store=brief_store,
        openai_client=_mock_openai_client,
    )

    out = runtime.analyze_document(
        company_ref="company/ULVR.L",
        document_ref="document/ULVR.L/2026-Q4-board-pack",
        document_text="Revenue grew. Margin improved. FX remains relevant.",
        document_type="board_pack",
        thesis_ref="thesis/ULVR.L/long/medium_term",
        operating_brief_id="brief/aion/v1",
        operating_brief_version="v1",
        generated_by="pytest",
    )

    assert out["company_ref"] == "company/ULVR.L"
    assert out["document_ref"] == "document/ULVR.L/2026-Q4-board-pack"
    assert out["analysis_packet"]["packet_type"] == "openai_document_analysis"
    assert out["analysis_packet"]["operating_brief"]["brief_id"] == "brief/aion/v1"
    assert out["analysis_response"]["company_profile"]["name"] == "Unilever PLC"
    assert out["analysis_response"]["quarter_summary"]["headline"] == "Stable demand with margin improvement."


def test_openai_document_analysis_runtime_rejects_wrong_brief_version(tmp_path):
    brief_store = OpenAIOperatingBriefStore(tmp_path)
    brief_store.save_operating_brief(
        brief_id="brief/aion/v1",
        version="v1",
        title="AION Operating Brief",
        content="System brief for document analysis.",
        generated_by="pytest",
    )

    runtime = OpenAIDocumentAnalysisRuntime(
        operating_brief_store=brief_store,
        openai_client=_mock_openai_client,
    )

    try:
        runtime.analyze_document(
            company_ref="company/ULVR.L",
            document_ref="document/ULVR.L/2026-Q4-board-pack",
            document_text="Test text",
            operating_brief_id="brief/aion/v1",
            operating_brief_version="v2",
            generated_by="pytest",
        )
        assert False, "Expected ValueError for version mismatch"
    except ValueError as e:
        assert "version mismatch" in str(e)