"""Encrypted, workspace-isolated ingestion and bounded local extraction for Legal documents."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import re
import shutil
import subprocess
import threading
import difflib
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from backend.modules.aion_business.runtime.legal_secure_storage import LegalEncryptedStore, LegalKeyStore
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.legal_resource_limits import (
    bounded_record_paths,
    ensure_workspace_record_write,
    estimated_encrypted_record_bytes,
)


class LegalDocumentError(ValueError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class LegalDocumentService:
    """Stores original bytes and derived text in one authenticated encrypted record.

    Extraction and OCR are local-only. Automated category suggestions are deliberately
    non-authoritative and always require a person to confirm them.
    """

    SCHEMA_VERSION = "tessaris.legal-document.v1"
    MAX_BYTES = 25 * 1024 * 1024
    MAX_TEXT_CHARS = 500_000
    MAX_PDF_PAGES = 200
    MAX_PDF_OCR_PAGES = 25
    MAX_PDF_OCR_IMAGES = 100
    MAX_IMAGE_PIXELS = 50_000_000
    ALLOWED = {
        "text/plain": {".txt", ".md", ".csv"},
        "application/pdf": {".pdf"},
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
        "image/png": {".png"},
        "image/jpeg": {".jpg", ".jpeg"},
        "image/tiff": {".tif", ".tiff"},
    }
    CATEGORY_TERMS = {
        "CONTRACT": ("agreement", "contract", "party", "parties", "term", "termination"),
        "TERMS_AND_CONDITIONS": ("terms and conditions", "terms of service", "limitation of liability"),
        "PRIVACY": ("privacy", "personal data", "data subject", "controller", "processor", "gdpr"),
        "EMPLOYMENT": ("employee", "employment", "salary", "holiday entitlement", "disciplinary"),
        "COMPLAINT": ("complaint", "dissatisfied", "refund", "consumer", "resolution"),
        "NOTICE": ("notice", "hereby", "effective date", "breach", "demand"),
        "INVOICE_OR_QUOTE": ("invoice", "quotation", "quote", "amount due", "vat"),
    }
    REVIEW_ENGINE_VERSION = "tessaris.legal-contract-review.rules.v1"
    REVIEW_RULES = (
        ("AUTO_RENEWAL", "Automatic renewal", ("automatic renewal", "automatically renew", "auto-renew"), "Check notice dates and renewal authority."),
        ("UNILATERAL_TERMINATION", "Unilateral termination", ("at our sole discretion", "at any time without cause", "without notice"), "Confirm whether termination rights are balanced and operationally workable."),
        ("UNLIMITED_LIABILITY", "Unlimited liability", ("unlimited liability", "without limitation as to amount"), "Escalate the liability exposure for authorised human review."),
        ("INDEMNITY", "Indemnity", ("indemnify", "indemnification", "hold harmless"), "Review scope, triggers, exclusions and insurance alignment."),
        ("EXCLUSIVITY", "Exclusivity", ("exclusive supplier", "exclusivity", "shall not engage"), "Check commercial scope, duration and exit rights."),
        ("RESTRICTIVE_COVENANT", "Restrictive covenant", ("non-compete", "non compete", "non-solicitation", "non solicitation"), "Seek qualified review for enforceability and proportionality."),
        ("PERSONAL_DATA", "Personal-data duties", ("personal data", "data controller", "data processor", "gdpr"), "Confirm roles, instructions, security, transfers and deletion terms."),
        ("LONG_PAYMENT_TERM", "Extended payment term", ("90 days", "one hundred and twenty days", "120 days"), "Check cash-flow impact and approval authority."),
    )

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        clock: Callable[[], datetime] = _utc_now,
        key_store: LegalKeyStore | None = None,
    ) -> None:
        self.root = Path(root) if root else AIONBusinessPaths.LEGAL_DOCUMENTS
        self.clock = clock
        self._lock = threading.RLock()
        self.key_store = key_store or LegalKeyStore(self.root)
        self.store = LegalEncryptedStore(self.root, purpose="document_records", key_store=self.key_store)

    def ingest(
        self,
        workspace_id: str,
        *,
        filename: str,
        media_type: str,
        content: bytes,
        actor_id: str,
        matter_id: str = "",
    ) -> dict[str, Any]:
        workspace = self._component(workspace_id, "workspace_id")
        clean_name = Path(str(filename or "").replace("\\", "/")).name.strip()
        if not clean_name or clean_name in {".", ".."}:
            raise LegalDocumentError("document_filename_required")
        if not content:
            raise LegalDocumentError("document_empty")
        if len(content) > self.MAX_BYTES:
            raise LegalDocumentError("document_too_large")
        mime = str(media_type or "").split(";", 1)[0].strip().lower()
        suffix = Path(clean_name).suffix.lower()
        if mime not in self.ALLOWED or suffix not in self.ALLOWED[mime]:
            raise LegalDocumentError("document_type_not_allowed")
        if suffix in {".docm", ".xlsm", ".pptm", ".exe", ".dmg", ".pkg", ".js", ".html"}:
            raise LegalDocumentError("active_or_executable_document_rejected")

        extraction = self._extract(mime, content)
        classification = self._classify(extraction.get("text", ""))
        document_id = f"document-{uuid4().hex}"
        now = _iso(self.clock())
        record = {
            "schema_version": self.SCHEMA_VERSION,
            "workspace_id": workspace,
            "document_id": document_id,
            "filename": clean_name[:240],
            "media_type": mime,
            "byte_length": len(content),
            "content_sha256": sha256(content).hexdigest(),
            "original_base64": base64.b64encode(content).decode("ascii"),
            "matter_id": self._component(matter_id, "matter_id") if matter_id else None,
            "extraction": extraction,
            "classification": classification,
            "review_status": "REVIEW_REQUIRED",
            "created_at": now,
            "updated_at": now,
            "created_by": str(actor_id or "unknown")[:160],
        }
        with self._lock:
            self._save(record)
        return self._public(record, include_text=True)

    def list_documents(self, workspace_id: str) -> list[dict[str, Any]]:
        workspace = self._component(workspace_id, "workspace_id")
        folder = self.root / workspace
        paths = bounded_record_paths(
            folder, ("document-*.enc",), error_type=LegalDocumentError,
        )
        records = [self._public(self.store.read(path, workspace_id=workspace, record_id=path.stem), include_text=False)
                   for path in paths]
        records.sort(key=lambda item: item["updated_at"], reverse=True)
        return records

    def get_document(self, workspace_id: str, document_id: str, *, include_text: bool = True) -> dict[str, Any]:
        return self._public(self._load(workspace_id, document_id), include_text=include_text)

    def original(self, workspace_id: str, document_id: str) -> tuple[str, str, bytes]:
        record = self._load(workspace_id, document_id)
        try:
            content = base64.b64decode(record["original_base64"], validate=True)
        except Exception:
            raise LegalDocumentError("document_payload_invalid") from None
        if sha256(content).hexdigest() != record.get("content_sha256"):
            raise LegalDocumentError("document_hash_mismatch")
        return record["filename"], record["media_type"], content

    def confirm_classification(
        self, workspace_id: str, document_id: str, *, actor_id: str, category: str,
    ) -> dict[str, Any]:
        clean = str(category or "").strip().upper().replace(" ", "_")
        if clean not in {*self.CATEGORY_TERMS, "OTHER"}:
            raise LegalDocumentError("unsupported_document_category")
        with self._lock:
            record = self._load(workspace_id, document_id)
            record["classification"]["confirmed_category"] = clean
            record["classification"]["confirmed_by"] = str(actor_id or "unknown")[:160]
            record["classification"]["confirmed_at"] = _iso(self.clock())
            record["review_status"] = "CLASSIFICATION_CONFIRMED"
            record["updated_at"] = _iso(self.clock())
            self._save(record)
        return self._public(record, include_text=True)

    def review_contract(self, workspace_id: str, document_id: str, *, actor_id: str) -> dict[str, Any]:
        """Run explainable local triage. This is not legal advice or a legal conclusion."""
        with self._lock:
            record = self._load(workspace_id, document_id)
            text = str((record.get("extraction") or {}).get("text") or "").strip()
            if not text:
                raise LegalDocumentError("document_text_required_for_review")
            lower = text.lower()
            findings = []
            for rule_id, title, terms, guidance in self.REVIEW_RULES:
                matched = next((term for term in terms if term in lower), None)
                if not matched:
                    continue
                start = max(0, lower.index(matched) - 100)
                end = min(len(text), lower.index(matched) + len(matched) + 160)
                findings.append({
                    "finding_id": f"finding-{sha256((rule_id + record['content_sha256']).encode()).hexdigest()[:20]}",
                    "rule_id": rule_id,
                    "title": title,
                    "matched_term": matched,
                    "source_excerpt": " ".join(text[start:end].split()),
                    "review_guidance": guidance,
                    "severity": "HIGH" if rule_id in {"UNLIMITED_LIABILITY", "RESTRICTIVE_COVENANT"} else "REVIEW",
                    "status": "HUMAN_REVIEW_REQUIRED",
                    "legal_conclusion": False,
                })
            if not any(term in lower for term in ("governing law", "laws of", "jurisdiction")):
                findings.append({
                    "finding_id": f"finding-{sha256(('GOVERNING_LAW_MISSING' + record['content_sha256']).encode()).hexdigest()[:20]}",
                    "rule_id": "GOVERNING_LAW_MISSING", "title": "Governing-law term not located",
                    "matched_term": None, "source_excerpt": None,
                    "review_guidance": "Confirm governing law and dispute forum with an authorised person or qualified professional.",
                    "severity": "REVIEW", "status": "HUMAN_REVIEW_REQUIRED", "legal_conclusion": False,
                })
            review = {
                "review_id": f"review-{uuid4().hex}",
                "engine_version": self.REVIEW_ENGINE_VERSION,
                "input_text_sha256": record["extraction"]["text_sha256"],
                "document_sha256": record["content_sha256"],
                "reviewed_at": _iso(self.clock()),
                "reviewed_by": str(actor_id or "unknown")[:160],
                "local_only": True,
                "status": "HUMAN_REVIEW_REQUIRED",
                "not_legal_advice": True,
                "clause_candidates": self._clause_candidates(text),
                "findings": findings,
                "finding_count": len(findings),
            }
            record.setdefault("contract_reviews", []).append(review)
            record["updated_at"] = _iso(self.clock())
            self._save(record)
        return review

    def compare_versions(
        self, workspace_id: str, base_document_id: str, proposed_document_id: str, *, actor_id: str,
    ) -> dict[str, Any]:
        base = self._load(workspace_id, base_document_id)
        proposed = self._load(workspace_id, proposed_document_id)
        base_text = str(base.get("extraction", {}).get("text") or "")
        proposed_text = str(proposed.get("extraction", {}).get("text") or "")
        if not base_text or not proposed_text:
            raise LegalDocumentError("document_text_required_for_comparison")
        diff = list(difflib.unified_diff(
            base_text.splitlines(), proposed_text.splitlines(),
            fromfile=base["filename"], tofile=proposed["filename"], lineterm="",
        ))
        comparison = {
            "comparison_id": f"comparison-{uuid4().hex}",
            "base_document_id": base["document_id"], "base_sha256": base["content_sha256"],
            "proposed_document_id": proposed["document_id"], "proposed_sha256": proposed["content_sha256"],
            "created_at": _iso(self.clock()), "created_by": str(actor_id or "unknown")[:160],
            "status": "HUMAN_REVIEW_REQUIRED", "legal_conclusion": False,
            "added_line_count": sum(1 for line in diff if line.startswith("+") and not line.startswith("+++")),
            "removed_line_count": sum(1 for line in diff if line.startswith("-") and not line.startswith("---")),
            "unified_diff": "\n".join(diff)[:200_000],
            "truncated": len("\n".join(diff)) > 200_000,
        }
        with self._lock:
            current = self._load(workspace_id, proposed_document_id)
            current.setdefault("version_comparisons", []).append(comparison)
            current["updated_at"] = _iso(self.clock())
            self._save(current)
        return comparison

    def create_redline(
        self, workspace_id: str, document_id: str, *, actor_id: str, finding_id: str,
        original_text: str, proposed_text: str, rationale: str,
    ) -> dict[str, Any]:
        original = str(original_text or "").strip()
        proposed = str(proposed_text or "").strip()
        if not original or not proposed or original == proposed:
            raise LegalDocumentError("redline_requires_distinct_original_and_proposed_text")
        with self._lock:
            record = self._load(workspace_id, document_id)
            source = str(record.get("extraction", {}).get("text") or "")
            if original not in source:
                raise LegalDocumentError("redline_original_text_not_found")
            known = {item.get("finding_id") for review in record.get("contract_reviews", []) for item in review.get("findings", [])}
            if finding_id and finding_id not in known:
                raise LegalDocumentError("redline_finding_not_found")
            redline = {
                "redline_id": f"redline-{uuid4().hex}", "finding_id": finding_id or None,
                "original_text": original[:20_000], "proposed_text": proposed[:20_000],
                "rationale": str(rationale or "").strip()[:5000], "status": "DRAFT_REQUIRES_HUMAN_APPROVAL",
                "created_at": _iso(self.clock()), "created_by": str(actor_id or "unknown")[:160],
                "modifies_original": False, "external_delivery_authorized": False,
            }
            record.setdefault("redlines", []).append(redline)
            record["updated_at"] = _iso(self.clock())
            self._save(record)
        return redline

    def record_negotiation_position(
        self, workspace_id: str, document_id: str, *, actor_id: str, issue: str,
        business_position: str, counterparty_position: str = "",
    ) -> dict[str, Any]:
        if not str(issue or "").strip() or not str(business_position or "").strip():
            raise LegalDocumentError("negotiation_issue_and_business_position_required")
        with self._lock:
            record = self._load(workspace_id, document_id)
            position = {
                "position_id": f"position-{uuid4().hex}", "issue": str(issue).strip()[:500],
                "business_position": str(business_position).strip()[:5000],
                "counterparty_position": str(counterparty_position or "").strip()[:5000],
                "status": "OPEN_REQUIRES_HUMAN_CONTROL", "created_at": _iso(self.clock()),
                "created_by": str(actor_id or "unknown")[:160], "external_delivery_authorized": False,
            }
            record.setdefault("negotiation_positions", []).append(position)
            record["updated_at"] = _iso(self.clock())
            self._save(record)
        return position

    def _extract(self, media_type: str, content: bytes) -> dict[str, Any]:
        if media_type == "text/plain":
            text = content.decode("utf-8-sig", errors="replace")
            return self._extraction(text, "NATIVE_TEXT", "COMPLETE")
        if media_type == "application/pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(BytesIO(content), strict=True)
                if len(reader.pages) > self.MAX_PDF_PAGES:
                    raise LegalDocumentError("pdf_page_limit_exceeded")
                text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
            except LegalDocumentError:
                raise
            except Exception:
                raise LegalDocumentError("pdf_invalid_or_encrypted") from None
            if text.strip():
                return self._extraction(text, "PDF_TEXT_LAYER", "COMPLETE", page_count=len(reader.pages))
            return self._ocr_pdf_images(reader)
        if media_type.endswith("wordprocessingml.document"):
            try:
                with ZipFile(BytesIO(content)) as archive:
                    members = archive.infolist()
                    if len(members) > 1000 or sum(item.file_size for item in members) > 50 * 1024 * 1024:
                        raise LegalDocumentError("docx_archive_limit_exceeded")
                    xml = archive.read("word/document.xml").decode("utf-8", errors="replace")
            except LegalDocumentError:
                raise
            except (BadZipFile, KeyError):
                raise LegalDocumentError("docx_invalid") from None
            text = re.sub(r"</w:p[^>]*>", "\n", xml)
            text = re.sub(r"<[^>]+>", "", text)
            text = (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                    .replace("&quot;", '"').replace("&apos;", "'"))
            return self._extraction(text, "DOCX_XML", "COMPLETE")
        return self._ocr_image(content)

    def _ocr_image(self, content: bytes) -> dict[str, Any]:
        try:
            from PIL import Image
            image = Image.open(BytesIO(content))
            if image.width * image.height > self.MAX_IMAGE_PIXELS:
                raise LegalDocumentError("image_pixel_limit_exceeded")
            image.verify()
        except LegalDocumentError:
            raise
        except Exception:
            raise LegalDocumentError("image_invalid") from None
        executable = shutil.which("tesseract")
        if not executable:
            return self._extraction("", "LOCAL_TESSERACT", "OCR_UNAVAILABLE",
                                    limitation="The local OCR engine is not installed.")
        try:
            result = subprocess.run(
                [executable, "stdin", "stdout", "--dpi", "300"], input=content,
                capture_output=True, timeout=60, check=False,
            )
        except subprocess.TimeoutExpired:
            raise LegalDocumentError("ocr_timeout") from None
        if result.returncode != 0:
            raise LegalDocumentError("ocr_failed")
        return self._extraction(result.stdout.decode("utf-8", errors="replace"), "LOCAL_TESSERACT", "COMPLETE")

    def _ocr_pdf_images(self, reader: Any) -> dict[str, Any]:
        if not shutil.which("tesseract"):
            return self._extraction("", "PDF_EMBEDDED_IMAGE_OCR", "OCR_UNAVAILABLE",
                                    page_count=len(reader.pages), limitation="The local OCR engine is not installed.")
        texts: list[str] = []
        image_count = 0
        pages_with_images = 0
        for page in reader.pages[: self.MAX_PDF_OCR_PAGES]:
            images = list(page.images)
            if images:
                pages_with_images += 1
            for image in images:
                if image_count >= self.MAX_PDF_OCR_IMAGES:
                    break
                image_count += 1
                extracted = self._ocr_image(image.data)
                if extracted["text"]:
                    texts.append(extracted["text"])
            if image_count >= self.MAX_PDF_OCR_IMAGES:
                break
        if not image_count:
            return self._extraction("", "PDF_EMBEDDED_IMAGE_OCR", "OCR_REQUIRED",
                                    page_count=len(reader.pages), limitation="No OCR-readable embedded page image was found.")
        truncated = len(reader.pages) > self.MAX_PDF_OCR_PAGES or image_count >= self.MAX_PDF_OCR_IMAGES
        return self._extraction(
            "\n\n".join(texts), "PDF_EMBEDDED_IMAGE_OCR", "PARTIAL" if truncated else "COMPLETE",
            page_count=len(reader.pages), pages_ocr_attempted=min(len(reader.pages), self.MAX_PDF_OCR_PAGES),
            pages_with_images=pages_with_images, image_count=image_count,
            limitation="OCR was bounded to the configured page or image limit." if truncated else None,
        )

    def _extraction(self, text: str, method: str, status: str, **extra: Any) -> dict[str, Any]:
        normalized = str(text or "").replace("\x00", "").strip()[: self.MAX_TEXT_CHARS]
        return {
            "status": status,
            "method": method,
            "local_only": True,
            "text": normalized,
            "text_sha256": sha256(normalized.encode("utf-8")).hexdigest(),
            "character_count": len(normalized),
            "truncated": len(str(text or "")) > self.MAX_TEXT_CHARS,
            **extra,
        }

    def _classify(self, text: str) -> dict[str, Any]:
        lower = str(text or "").lower()
        scores = {category: sum(lower.count(term) for term in terms) for category, terms in self.CATEGORY_TERMS.items()}
        category, score = max(scores.items(), key=lambda item: item[1]) if scores else ("OTHER", 0)
        suggested = category if score else "OTHER"
        return {
            "suggested_category": suggested,
            "confidence": "MEDIUM" if score >= 4 else "LOW",
            "matched_term_count": score,
            "status": "REVIEW_REQUIRED",
            "human_confirmation_required": True,
            "legal_determination": False,
            "confirmed_category": None,
        }

    def _clause_candidates(self, text: str) -> list[dict[str, Any]]:
        candidates = []
        for index, line in enumerate(text.splitlines()):
            clean = " ".join(line.split()).strip()
            if not clean or len(clean) > 180:
                continue
            heading_like = bool(re.match(r"^(?:\d+(?:\.\d+)*[.)]?\s+|[A-Z][A-Z\s&/-]{3,})", clean))
            if heading_like:
                candidates.append({"line_number": index + 1, "heading": clean[:180], "status": "CANDIDATE_REQUIRES_REVIEW"})
            if len(candidates) >= 100:
                break
        return candidates

    def _public(self, record: dict[str, Any], *, include_text: bool) -> dict[str, Any]:
        result = {key: value for key, value in record.items() if key != "original_base64"}
        result["original_available"] = True
        if not include_text:
            result["extraction"] = {key: value for key, value in result["extraction"].items() if key != "text"}
        return result

    def _load(self, workspace_id: str, document_id: str) -> dict[str, Any]:
        workspace = self._component(workspace_id, "workspace_id")
        document = self._component(document_id, "document_id")
        path = self._path(workspace, document)
        if not path.exists():
            raise LegalDocumentError("document_not_found")
        return self.store.read(path, workspace_id=workspace, record_id=document)

    def _path(self, workspace_id: str, document_id: str) -> Path:
        return self.root / self._component(workspace_id, "workspace_id") / f"{self._component(document_id, 'document_id')}.enc"

    def _save(self, record: dict[str, Any]) -> None:
        path = self._path(record["workspace_id"], record["document_id"])
        ensure_workspace_record_write(
            workspace_folder=path.parent,
            record_path=path,
            record_patterns=("document-*.enc",),
            estimated_bytes=estimated_encrypted_record_bytes(record),
            error_type=LegalDocumentError,
        )
        self.store.write(
            path, record,
            workspace_id=record["workspace_id"], record_id=record["document_id"],
        )

    @staticmethod
    def _component(value: str, field: str) -> str:
        clean = str(value or "").strip()
        if not clean or not re.fullmatch(r"[A-Za-z0-9_.-]{1,180}", clean):
            raise LegalDocumentError(f"invalid_{field}")
        return clean
