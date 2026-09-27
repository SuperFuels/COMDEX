from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import json
import subprocess
from zipfile import ZipFile

import pytest

from backend.modules.aion_business.runtime.legal_document_service import LegalDocumentError, LegalDocumentService


NOW = datetime(2026, 9, 26, 15, 0, tzinfo=timezone.utc)


def _service(tmp_path):
    return LegalDocumentService(tmp_path / "legal-documents", clock=lambda: NOW)


def _docx(text: str) -> bytes:
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("word/document.xml", f'<w:document xmlns:w="x"><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>')
    return stream.getvalue()


def test_plaintext_ingestion_is_encrypted_hashed_classified_and_workspace_isolated(tmp_path):
    service = _service(tmp_path)
    content = b"Supplier Agreement\nThese parties agree to the contract term and termination provisions."
    document = service.ingest(
        "workspace-a", filename="supplier-agreement.txt", media_type="text/plain",
        content=content, actor_id="owner-1", matter_id="matter-1",
    )
    assert document["classification"]["suggested_category"] == "CONTRACT"
    assert document["classification"]["human_confirmation_required"] is True
    assert document["classification"]["legal_determination"] is False
    assert document["review_status"] == "REVIEW_REQUIRED"
    assert document["original_available"] is True
    path = service._path("workspace-a", document["document_id"])
    encrypted = path.read_text(encoding="utf-8")
    assert "Supplier Agreement" not in encrypted
    assert content.decode() not in encrypted
    assert service.list_documents("workspace-a")[0]["extraction"].get("text") is None
    with pytest.raises(LegalDocumentError, match="document_not_found"):
        service.get_document("workspace-b", document["document_id"])
    name, media_type, exact = service.original("workspace-a", document["document_id"])
    assert (name, media_type, exact) == ("supplier-agreement.txt", "text/plain", content)


def test_docx_text_is_extracted_without_macros_and_confirmation_is_a_human_action(tmp_path):
    service = _service(tmp_path)
    document = service.ingest(
        "workspace-a", filename="privacy.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=_docx("Privacy notice for personal data and GDPR controller duties"), actor_id="owner-1",
    )
    assert "Privacy notice" in document["extraction"]["text"]
    assert document["classification"]["suggested_category"] == "PRIVACY"
    confirmed = service.confirm_classification(
        "workspace-a", document["document_id"], actor_id="owner-1", category="PRIVACY",
    )
    assert confirmed["review_status"] == "CLASSIFICATION_CONFIRMED"
    assert confirmed["classification"]["confirmed_by"] == "owner-1"


def test_image_ocr_is_local_bounded_and_review_required(tmp_path, monkeypatch):
    from PIL import Image

    stream = BytesIO()
    Image.new("RGB", (30, 30), "white").save(stream, format="PNG")
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/tesseract")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(
        args[0], 0, stdout=b"Customer complaint and refund resolution", stderr=b"",
    ))
    document = _service(tmp_path).ingest(
        "workspace-a", filename="letter.png", media_type="image/png",
        content=stream.getvalue(), actor_id="owner-1",
    )
    assert document["extraction"]["method"] == "LOCAL_TESSERACT"
    assert document["extraction"]["local_only"] is True
    assert document["classification"]["suggested_category"] == "COMPLAINT"


def test_scanned_pdf_and_missing_ocr_are_explicit_not_fabricated(tmp_path, monkeypatch):
    pytest.importorskip("pypdf")
    from pypdf import PdfWriter

    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(output)
    document = _service(tmp_path).ingest(
        "workspace-a", filename="scan.pdf", media_type="application/pdf",
        content=output.getvalue(), actor_id="owner-1",
    )
    assert document["extraction"]["status"] in {"OCR_REQUIRED", "OCR_UNAVAILABLE"}
    assert document["classification"]["suggested_category"] == "OTHER"


def test_scanned_image_pdf_is_ocr_processed_locally(tmp_path, monkeypatch):
    from PIL import Image

    output = BytesIO()
    Image.new("RGB", (100, 100), "white").save(output, format="PDF")
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/tesseract")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(
        args[0], 0, stdout=b"Employment contract salary and holiday entitlement", stderr=b"",
    ))
    document = _service(tmp_path).ingest(
        "workspace-a", filename="scan.pdf", media_type="application/pdf",
        content=output.getvalue(), actor_id="owner-1",
    )
    assert document["extraction"]["method"] == "PDF_EMBEDDED_IMAGE_OCR"
    assert document["extraction"]["status"] == "COMPLETE"
    assert document["classification"]["suggested_category"] == "EMPLOYMENT"


def test_unsafe_wrong_or_oversized_files_are_rejected(tmp_path):
    service = _service(tmp_path)
    with pytest.raises(LegalDocumentError, match="document_type_not_allowed"):
        service.ingest("workspace-a", filename="payload.html", media_type="text/html", content=b"x", actor_id="owner")
    with pytest.raises(LegalDocumentError, match="document_type_not_allowed"):
        service.ingest("workspace-a", filename="wrong.pdf", media_type="text/plain", content=b"x", actor_id="owner")
    with pytest.raises(LegalDocumentError, match="document_too_large"):
        service.ingest("workspace-a", filename="huge.txt", media_type="text/plain",
                       content=b"x" * (service.MAX_BYTES + 1), actor_id="owner")


def test_encrypted_record_tampering_is_rejected(tmp_path):
    service = _service(tmp_path)
    document = service.ingest(
        "workspace-a", filename="notice.txt", media_type="text/plain", content=b"Notice",
        actor_id="owner-1",
    )
    path = service._path("workspace-a", document["document_id"])
    envelope = json.loads(path.read_text(encoding="utf-8"))
    envelope["ciphertext_base64"] = ("A" if envelope["ciphertext_base64"][0] != "A" else "B") + envelope["ciphertext_base64"][1:]
    path.write_text(json.dumps(envelope), encoding="utf-8")
    with pytest.raises(PermissionError, match="could not be authenticated"):
        service.get_document("workspace-a", document["document_id"])


def test_contract_review_extracts_clause_candidates_and_explainable_risk_signals(tmp_path):
    service = _service(tmp_path)
    document = service.ingest(
        "workspace-a", filename="agreement.txt", media_type="text/plain",
        content=(b"1. AUTOMATIC RENEWAL\nThis agreement shall automatically renew.\n"
                 b"2. LIABILITY\nThe supplier has unlimited liability and shall indemnify the customer."),
        actor_id="owner-1",
    )
    review = service.review_contract("workspace-a", document["document_id"], actor_id="owner-1")
    rules = {item["rule_id"] for item in review["findings"]}
    assert {"AUTO_RENEWAL", "UNLIMITED_LIABILITY", "INDEMNITY", "GOVERNING_LAW_MISSING"} <= rules
    assert review["clause_candidates"][0]["status"] == "CANDIDATE_REQUIRES_REVIEW"
    assert review["status"] == "HUMAN_REVIEW_REQUIRED"
    assert review["not_legal_advice"] is True
    stored = service.get_document("workspace-a", document["document_id"])
    assert stored["contract_reviews"][0]["input_text_sha256"] == document["extraction"]["text_sha256"]


def test_version_comparison_redline_and_negotiation_are_controlled_non_destructive_records(tmp_path):
    service = _service(tmp_path)
    base = service.ingest(
        "workspace-a", filename="agreement-v1.txt", media_type="text/plain",
        content=b"1. PAYMENT\nPayment is due in 30 days.\n2. LAW\nGoverned by the laws of Ireland.", actor_id="owner-1",
    )
    proposed = service.ingest(
        "workspace-a", filename="agreement-v2.txt", media_type="text/plain",
        content=b"1. PAYMENT\nPayment is due in 90 days.\n2. LAW\nGoverned by the laws of Ireland.", actor_id="owner-1",
    )
    review = service.review_contract("workspace-a", proposed["document_id"], actor_id="owner-1")
    finding = next(item for item in review["findings"] if item["rule_id"] == "LONG_PAYMENT_TERM")
    comparison = service.compare_versions(
        "workspace-a", base["document_id"], proposed["document_id"], actor_id="owner-1",
    )
    assert comparison["added_line_count"] == 1
    assert comparison["removed_line_count"] == 1
    assert "+Payment is due in 90 days." in comparison["unified_diff"]
    redline = service.create_redline(
        "workspace-a", proposed["document_id"], actor_id="owner-1", finding_id=finding["finding_id"],
        original_text="Payment is due in 90 days.", proposed_text="Payment is due in 30 days.",
        rationale="Protect working capital.",
    )
    assert redline["modifies_original"] is False
    assert redline["external_delivery_authorized"] is False
    position = service.record_negotiation_position(
        "workspace-a", proposed["document_id"], actor_id="owner-1", issue="Payment period",
        business_position="30 days", counterparty_position="90 days",
    )
    assert position["status"] == "OPEN_REQUIRES_HUMAN_CONTROL"
    assert service.original("workspace-a", proposed["document_id"])[2] == b"1. PAYMENT\nPayment is due in 90 days.\n2. LAW\nGoverned by the laws of Ireland."


def test_redline_rejects_text_not_bound_to_the_exact_source_document(tmp_path):
    service = _service(tmp_path)
    document = service.ingest(
        "workspace-a", filename="agreement.txt", media_type="text/plain",
        content=b"Exact original clause", actor_id="owner-1",
    )
    with pytest.raises(LegalDocumentError, match="redline_original_text_not_found"):
        service.create_redline(
            "workspace-a", document["document_id"], actor_id="owner-1", finding_id="",
            original_text="Different clause", proposed_text="Replacement", rationale="",
        )
