from pathlib import Path

import pytest

from backend.modules.aion_cognition.native_document_ingestion import (
    DocumentExtractionError,
    NativeDocumentExtractor,
)


def _write_text_pdf(path: Path, text: str) -> None:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(objects)+1}\n".encode())
    data.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(
        f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    path.write_bytes(bytes(data))


def test_text_layer_pdf_is_cleaned_scored_and_released(tmp_path: Path):
    pdf = tmp_path / "book.pdf"
    _write_text_pdf(
        pdf,
        "Mira inspected the unusual specimen in the laboratory. "
        "The careful examination confirmed the earlier scientific report. "
        "She recorded the evidence before discussing the result with her colleague. "
        "Her colleague repeated the procedure under controlled conditions and obtained the same result. "
        "Together they documented the method, observations, limitations, and conclusion for later review.",
    )
    extractor = NativeDocumentExtractor(repo_root=tmp_path, minimum_quality=0.3)

    result = extractor.extract(pdf)

    assert result["status"] == "ready"
    assert result["format"] == "pdf"
    assert result["method"] == "pdf_text_layer"
    assert result["quality"]["word_count"] >= 20
    assert "Mira inspected" in result["text"]
    assert result["model_used"] is False


def test_scanned_pdf_uses_local_vision_ocr_fallback(tmp_path: Path, monkeypatch):
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"placeholder")
    extractor = NativeDocumentExtractor(repo_root=tmp_path, minimum_quality=0.3)
    monkeypatch.setattr(extractor, "_pdf_text_pages", lambda path, limit: ([""], {"page_count": 1}))
    monkeypatch.setattr(
        extractor, "_macos_vision_ocr",
        lambda path, count: ([
            "Leona repaired the navigation instrument before sunrise. "
            "The successful repair allowed the expedition to continue safely."
        ], {"page_count": 1, "ocr_pages_attempted": 1, "ocr_truncated": False}),
    )

    result = extractor.extract(pdf)

    assert result["method"] == "macos_vision_ocr"
    assert "pdf_text_layer_was_missing_or_unusable" in result["warnings"]
    assert result["quality"]["score"] >= 0.3


def test_unreadable_ocr_is_quarantined_instead_of_becoming_lessons(tmp_path: Path, monkeypatch):
    pdf = tmp_path / "bad-scan.pdf"
    pdf.write_bytes(b"placeholder")
    extractor = NativeDocumentExtractor(repo_root=tmp_path, minimum_quality=0.6)
    monkeypatch.setattr(extractor, "_pdf_text_pages", lambda path, limit: ([""], {"page_count": 1}))
    monkeypatch.setattr(
        extractor, "_macos_vision_ocr",
        lambda path, count: (["x x x � �"], {"page_count": 1, "ocr_pages_attempted": 1}),
    )

    with pytest.raises(DocumentExtractionError) as error:
        extractor.extract(pdf)

    assert error.value.code == "document_quality_below_threshold"
    assert error.value.detail["status"] == "quarantined"


def test_cleaner_removes_repeated_headers_page_numbers_and_repairs_hyphens(tmp_path: Path):
    extractor = NativeDocumentExtractor(repo_root=tmp_path)
    pages = [
        f"Scientific Methods\nPage {index}\nIntroduction {index}\nThe investi-\n"
        f"gator tested a new hypothesis carefully.\nObservation {index}\n"
        f"Conclusion {index}\nEnd note {index}"
        for index in range(1, 5)
    ]

    text, warnings = extractor._clean_pages(pages)

    assert "Scientific Methods" not in text
    assert "Page 1" not in text
    assert "investigator" in text
    assert warnings
