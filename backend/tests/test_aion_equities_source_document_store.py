from __future__ import annotations

from backend.modules.aion_equities.source_document_store import SourceDocumentStore


def test_source_document_store_saves_and_loads_document(tmp_path):
    store = SourceDocumentStore(tmp_path)

    payload = store.save_source_document(
        company_ref="company/PAGE.L",
        source_type="quarterly_report",
        fiscal_period_ref="2026Q1",
        published_at="2026-04-15T07:00:00Z",
        source_file_ref="files/page_q1_2026.pdf",
        parsed_text_ref="parsed/page_q1_2026.txt",
        tables_ref="tables/page_q1_2026.json",
        ingestion_status="registered",
        provenance_hash="sha256:abc123",
        generated_by="pytest",
    )

    loaded = store.load_source_document("company/PAGE.L", payload["document_id"])

    assert loaded["document_id"] == payload["document_id"]
    assert loaded["company_ref"] == "company/PAGE.L"
    assert loaded["source_type"] == "quarterly_report"
    assert loaded["fiscal_period_ref"] == "2026Q1"
    assert loaded["source_file_ref"] == "files/page_q1_2026.pdf"
    assert loaded["parsed_text_ref"] == "parsed/page_q1_2026.txt"
    assert loaded["tables_ref"] == "tables/page_q1_2026.json"
    assert loaded["provenance_hash"] == "sha256:abc123"


def test_source_document_store_lists_company_documents(tmp_path):
    store = SourceDocumentStore(tmp_path)

    doc1 = store.save_source_document(
        company_ref="company/PAGE.L",
        source_type="quarterly_report",
        fiscal_period_ref="2026Q1",
        source_file_ref="files/a.pdf",
    )
    doc2 = store.save_source_document(
        company_ref="company/PAGE.L",
        source_type="presentation",
        fiscal_period_ref="2026Q1",
        source_file_ref="files/b.pdf",
        document_id="company/PAGE.L/source_document/2026Q1/presentation_v2",
    )

    ids = store.list_source_documents("company/PAGE.L")

    assert doc1["document_id"] in ids
    assert doc2["document_id"] in ids
    assert len(ids) == 2


def test_source_document_store_lists_documents_for_period(tmp_path):
    store = SourceDocumentStore(tmp_path)

    store.save_source_document(
        company_ref="company/ULVR.L",
        source_type="quarterly_report",
        fiscal_period_ref="2026Q1",
        source_file_ref="files/q1.pdf",
    )
    store.save_source_document(
        company_ref="company/ULVR.L",
        source_type="trading_update",
        fiscal_period_ref="2026Q2",
        source_file_ref="files/q2.pdf",
    )

    docs = store.list_source_documents_for_period("company/ULVR.L", "2026Q1")

    assert len(docs) == 1
    assert docs[0]["fiscal_period_ref"] == "2026Q1"


def test_source_document_store_load_by_id(tmp_path):
    store = SourceDocumentStore(tmp_path)

    payload = store.save_source_document(
        company_ref="company/ULVR.L",
        source_type="annual_report",
        fiscal_period_ref="2025FY",
        source_file_ref="files/annual.pdf",
    )

    loaded = store.load_source_document_by_id(payload["document_id"])
    assert loaded["document_id"] == payload["document_id"]
    assert loaded["company_ref"] == "company/ULVR.L"