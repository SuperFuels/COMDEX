"""Local book/document extraction and quality control for Aion's reader."""
from __future__ import annotations

from collections import Counter
from html import unescape
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any
import zipfile


SUPPORTED_DOCUMENT_EXTENSIONS = {".txt", ".text", ".md", ".epub", ".pdf"}
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")


class DocumentExtractionError(ValueError):
    """The document could not safely be released into the reading queue."""

    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail or {}


class NativeDocumentExtractor:
    """Extract readable local text without using a language model or cloud API."""

    def __init__(self, *, repo_root: Path | str, minimum_quality: float = 0.48,
                 max_pdf_pages: int = 1200, max_ocr_pages: int = 400) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.minimum_quality = max(0.0, min(1.0, float(minimum_quality)))
        self.max_pdf_pages = max(1, int(max_pdf_pages))
        self.max_ocr_pages = max(1, int(max_ocr_pages))
        self.ocr_script = Path(__file__).with_name("macos_pdf_ocr.swift")

    @staticmethod
    def _epub_pages(path: Path) -> list[str]:
        pages: list[str] = []
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > 10_000 or sum(item.file_size for item in members) > 250_000_000:
                raise DocumentExtractionError("epub_archive_limit_exceeded")
            for name in sorted(archive.namelist()):
                if not name.lower().endswith((".xhtml", ".html", ".htm")):
                    continue
                raw = archive.read(name).decode("utf-8", errors="ignore")
                raw = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
                raw = re.sub(r"(?i)</(?:p|div|h[1-6]|li|blockquote|section)>", "\n\n", raw)
                pages.append(unescape(re.sub(r"<[^>]+>", " ", raw)))
        return pages

    @staticmethod
    def _spacing_damage(text: str) -> tuple[float, float]:
        words = WORD_RE.findall(str(text or ""))
        if not words:
            return (1.0, 100.0)
        return (
            sum(len(word) > 16 for word in words) / len(words),
            sum(map(len, words)) / len(words),
        )

    @staticmethod
    def _pdf_text_pages(path: Path, max_pages: int) -> tuple[list[str], dict[str, Any]]:
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path), strict=False)
        except Exception as exc:
            raise DocumentExtractionError(
                "pdf_invalid_or_encrypted", detail={"error": type(exc).__name__},
            ) from None
        if reader.is_encrypted:
            try:
                if reader.decrypt("") == 0:
                    raise DocumentExtractionError("pdf_password_required")
            except DocumentExtractionError:
                raise
            except Exception:
                raise DocumentExtractionError("pdf_password_required") from None
        page_count = len(reader.pages)
        if page_count > max_pages:
            raise DocumentExtractionError(
                "pdf_page_limit_exceeded", detail={"page_count": page_count, "limit": max_pages},
            )
        pages: list[str] = []
        failed_pages = 0
        for page in reader.pages:
            try:
                plain = page.extract_text() or ""
                layout = page.extract_text(extraction_mode="layout") or ""
                pages.append(min((plain, layout), key=NativeDocumentExtractor._spacing_damage))
            except Exception:
                failed_pages += 1
                try:
                    pages.append(page.extract_text() or "")
                except Exception:
                    pages.append("")
        document_metadata = reader.metadata or {}
        return pages, {
            "page_count": page_count, "failed_text_pages": failed_pages,
            "document_title": str(document_metadata.get("/Title") or "").strip()[:300],
            "document_author": str(document_metadata.get("/Author") or "").strip()[:300],
        }

    def _macos_vision_ocr(self, path: Path, page_count: int) -> tuple[list[str], dict[str, Any]]:
        swift = shutil.which("swift")
        if not swift or not self.ocr_script.is_file():
            raise DocumentExtractionError(
                "pdf_ocr_unavailable", detail={"page_count": page_count},
            )
        pages_to_read = min(page_count, self.max_ocr_pages)
        try:
            result = subprocess.run(
                [swift, str(self.ocr_script), str(path), str(pages_to_read)],
                capture_output=True, timeout=max(180, pages_to_read * 18), check=False,
            )
        except subprocess.TimeoutExpired:
            raise DocumentExtractionError(
                "pdf_ocr_timeout", detail={"pages_attempted": pages_to_read},
            ) from None
        if result.returncode != 0:
            raise DocumentExtractionError(
                "pdf_ocr_failed",
                detail={"pages_attempted": pages_to_read,
                        "stderr": result.stderr.decode("utf-8", errors="ignore")[-1000:]},
            )
        try:
            payload = json.loads(result.stdout.decode("utf-8", errors="replace"))
            pages = [str(value or "") for value in payload.get("pages") or []]
        except (json.JSONDecodeError, AttributeError):
            raise DocumentExtractionError("pdf_ocr_invalid_output") from None
        return pages, {
            "page_count": page_count,
            "ocr_pages_attempted": pages_to_read,
            "ocr_truncated": page_count > pages_to_read,
        }

    @staticmethod
    def _clean_pages(pages: list[str]) -> tuple[str, list[str]]:
        normalized_pages: list[list[str]] = []
        edge_counts: Counter[str] = Counter()
        for raw_page in pages:
            raw_page = str(raw_page or "").replace("\x00", " ").replace("\r", "\n")
            lines = [re.sub(r"\s+", " ", line).strip() for line in raw_page.splitlines()]
            lines = [line for line in lines if line]
            normalized_pages.append(lines)
            for line in [*lines[:3], *lines[-3:]]:
                key = re.sub(r"\d+", "#", line.lower()).strip(" -–—|•")
                if 2 <= len(key) <= 100:
                    edge_counts[key] += 1
        repeated = {
            line for line, count in edge_counts.items()
            if len(pages) >= 3 and count >= max(3, round(len(pages) * 0.45))
        }
        warnings: list[str] = []
        cleaned_pages: list[str] = []
        removed = 0
        for lines in normalized_pages:
            kept: list[str] = []
            for index, line in enumerate(lines):
                key = re.sub(r"\d+", "#", line.lower()).strip(" -–—|•")
                is_edge = index < 3 or index >= max(0, len(lines) - 3)
                if is_edge and key in repeated:
                    removed += 1
                    continue
                if re.fullmatch(r"(?:page\s+)?[ivxlcdm\d]+", line, re.I):
                    removed += 1
                    continue
                kept.append(line)
            page = "\n".join(kept)
            page = re.sub(r"(?<=\w)-\n(?=[a-z])", "", page)
            page = re.sub(r"(?<![.!?:;])\n(?=[a-z])", " ", page)
            page = re.sub(r"[ \t]+", " ", page)
            page = re.sub(r"\n{3,}", "\n\n", page).strip()
            if page:
                cleaned_pages.append(page)
        if removed:
            warnings.append(f"removed_{removed}_repeated_or_page_number_lines")
        return "\n\n".join(cleaned_pages), warnings

    @staticmethod
    def quality(text: str, *, page_count: int = 1) -> dict[str, Any]:
        value = str(text or "")
        words = WORD_RE.findall(value)
        characters = len(value)
        letters = sum(character.isalpha() for character in value)
        visible = sum(not character.isspace() for character in value)
        replacement = value.count("�") + value.count("\ufffd")
        alpha_ratio = letters / visible if visible else 0.0
        replacement_ratio = replacement / max(1, characters)
        average_word_length = sum(map(len, words)) / max(1, len(words))
        long_word_ratio = sum(len(word) > 16 for word in words) / max(1, len(words))
        sentence_marks = len(re.findall(r"[.!?](?:[\"'’”)]|\s|$)", value))
        words_per_page = len(words) / max(1, page_count)
        score = 0.0
        score += 0.22 if len(words) >= 40 else 0.22 * min(1.0, len(words) / 40)
        score += 0.25 * min(1.0, alpha_ratio / 0.62)
        score += 0.18 if 3.2 <= average_word_length <= 9.5 else 0.08
        score += 0.20 * min(1.0, sentence_marks / max(1, len(words) / 35))
        score += 0.15 * min(1.0, words_per_page / 45)
        score -= min(0.35, replacement_ratio * 25)
        score -= min(0.55, long_word_ratio * 4)
        return {
            "score": round(max(0.0, min(1.0, score)), 4),
            "character_count": characters,
            "word_count": len(words),
            "page_count": page_count,
            "alpha_ratio": round(alpha_ratio, 4),
            "replacement_ratio": round(replacement_ratio, 6),
            "average_word_length": round(average_word_length, 3),
            "long_word_ratio": round(long_word_ratio, 4),
            "sentence_marks": sentence_marks,
        }

    def extract(self, path: Path | str) -> dict[str, Any]:
        candidate = Path(path).expanduser().resolve()
        suffix = candidate.suffix.lower()
        if not candidate.is_file() or suffix not in SUPPORTED_DOCUMENT_EXTENSIONS:
            raise DocumentExtractionError("unsupported_or_missing_reading_source")
        warnings: list[str] = []
        method = "native_text"
        metadata: dict[str, Any] = {}
        if suffix == ".epub":
            try:
                pages = self._epub_pages(candidate)
            except (OSError, zipfile.BadZipFile):
                raise DocumentExtractionError("epub_invalid") from None
            method = "epub_semantic_html"
        elif suffix == ".pdf":
            pages, metadata = self._pdf_text_pages(candidate, self.max_pdf_pages)
            raw_quality = self.quality("\n\n".join(pages), page_count=len(pages))
            sparse_threshold = max(35, len(pages) * 12)
            if (raw_quality["word_count"] < sparse_threshold
                    or raw_quality["score"] < 0.34
                    or raw_quality["long_word_ratio"] > 0.08):
                pages, ocr_metadata = self._macos_vision_ocr(
                    candidate, int(metadata.get("page_count") or len(pages)),
                )
                metadata.update(ocr_metadata)
                method = "macos_vision_ocr"
                warnings.append("pdf_text_layer_was_missing_or_unusable")
            else:
                method = "pdf_text_layer"
        else:
            pages = [candidate.read_text(encoding="utf-8-sig", errors="replace")]
        text, cleaning_warnings = self._clean_pages(pages)
        warnings.extend(cleaning_warnings)
        quality = self.quality(text, page_count=max(1, len(pages)))
        status = "ready" if quality["score"] >= self.minimum_quality else "quarantined"
        result = {
            "status": status, "method": method, "format": suffix.lstrip("."),
            "text": text, "quality": quality, "warnings": warnings,
            "local_only": True, "model_used": False, **metadata,
        }
        if status != "ready":
            raise DocumentExtractionError("document_quality_below_threshold", detail=result)
        return result


__all__ = [
    "DocumentExtractionError", "NativeDocumentExtractor",
    "SUPPORTED_DOCUMENT_EXTENSIONS",
]
