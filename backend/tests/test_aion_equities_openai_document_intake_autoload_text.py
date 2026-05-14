# /workspaces/COMDEX/backend/tests/test_aion_equities_openai_document_intake_autoload_text.py
from __future__ import annotations

from pathlib import Path

from backend.modules.aion_equities.openai_company_profile_mapper import OpenAICompanyProfileMapper
from backend.modules.aion_equities.openai_document_analysis_runtime import OpenAIDocumentAnalysisRuntime
from backend.modules.aion_equities.openai_document_intake_runtime import OpenAIDocumentIntakeRuntime
from backend.modules.aion_equities.openai_operating_brief_store import OpenAIOperatingBriefStore
from backend.modules.aion_equities.quarter_event_store import QuarterEventStore
from backend.modules.aion_equities.source_document_store import SourceDocumentStore


def test_openai_document_intake_runtime_autoloads_document_text_from_parsed_text_ref(tmp_path):
    # --- operating brief ---
    brief_store = OpenAIOperatingBriefStore(base_dir=tmp_path)
    saved = brief_store.save_operating_brief(
        brief_id="brief/aion_equities_default",
        version="v1",
        title="AION Equities",
        summary="Operating brief",
        brief_text="Analyze company documents and return structured output.",
    )
    brief_store.set_active_brief(saved["brief_id"])

    # --- write a fake extracted text file ---
    runtime_dir = Path(tmp_path) / "parsed"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    parsed_path = runtime_dir / "boardpack.txt"
    parsed_text = "THIS IS THE PARSED BOARD PACK TEXT"
    parsed_path.write_text(parsed_text, encoding="utf-8")

    # --- register source doc with parsed_text_ref -> that file ---
    source_store = SourceDocumentStore(tmp_path)
    doc = source_store.save_source_document(
        company_ref="company/TSCO.L",
        source_type="board_pack",
        fiscal_period_ref="2026-Q1",
        source_file_ref="files/tsco_boardpack.pdf",
        parsed_text_ref=str(parsed_path),  # absolute path is supported
        tables_ref=None,
        provenance_hash="sha256:test",
        ingestion_status="registered",
        generated_by="test",
    )

    seen = {"text": None}

    def fake_openai_client(packet):
        # Assert packet includes autoloaded content
        seen["text"] = packet["document"]["text"]
        assert parsed_text in packet["document"]["text"]

        # Return minimal valid analysis payload
        return {
            "company_profile": {
                "name": "Tesco",
                "sector": "consumer_staples",
                "country": "UK",
                "description": "Retailer",
            },
            "quarter_summary": {
                "headline": "Stable quarter",
                "summary": "Defensive trading held up",
                "key_numbers": {"like_for_like_sales_pct": 3.1},
                "fiscal_period": "2026-Q1",
            },
        }

    analysis_runtime = OpenAIDocumentAnalysisRuntime(
        operating_brief_store=brief_store,
        openai_client=fake_openai_client,
    )

    intake = OpenAIDocumentIntakeRuntime(
        document_analysis_runtime=analysis_runtime,
        company_profile_mapper=OpenAICompanyProfileMapper(),
        quarter_event_store=QuarterEventStore(base_dir=tmp_path),
        # NEW wiring:
        source_document_store=source_store,
        document_text_base_dir=tmp_path,  # not used for absolute paths, but fine
    )

    out = intake.run_document_intake(
        company_ref="company/TSCO.L",
        document_ref=doc["document_id"],
        document_text="",  # triggers autoload
        document_type="board_pack",
        autoload_document_text=True,
    )

    assert out["company_ref"] == "company/TSCO.L"
    assert seen["text"] is not None
    assert parsed_text in seen["text"]
    assert out["persisted_objects"]["resolved_document_text_len"] >= len(parsed_text)