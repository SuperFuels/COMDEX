"""Bounded, provider-neutral preparation of explicitly selected chat attachments."""
from __future__ import annotations

from html import unescape
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping
from zipfile import BadZipFile, ZipFile


MAX_ATTACHMENTS = 20
MAX_PREVIEW_CHARS = 12_000
MAX_FOLDER_ITEMS = 80
PACKAGE_EXTENSIONS = {".pages", ".numbers", ".key", ".rtfd"}
TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".jsonl",
    ".html", ".htm", ".xml", ".yaml", ".yml", ".log", ".rtf",
    ".py", ".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".sql",
    ".sh", ".zsh", ".toml", ".ini", ".cfg",
}


def _plain_xml(value: str) -> str:
    value = re.sub(r"</w:p>|</text:p>|<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\n{3,}", "\n\n", unescape(value)).strip()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:MAX_PREVIEW_CHARS]
    except OSError:
        return ""


def _read_docx(path: Path) -> str:
    try:
        with ZipFile(path) as archive:
            return _plain_xml(archive.read("word/document.xml").decode("utf-8", "replace"))[:MAX_PREVIEW_CHARS]
    except (OSError, KeyError, BadZipFile):
        return ""


def _read_xlsx(path: Path) -> str:
    try:
        with ZipFile(path) as archive:
            names = set(archive.namelist())
            parts: list[str] = []
            if "xl/sharedStrings.xml" in names:
                parts.append(_plain_xml(archive.read("xl/sharedStrings.xml").decode("utf-8", "replace")))
            for name in sorted(item for item in names if re.match(r"xl/worksheets/sheet\d+\.xml$", item))[:3]:
                parts.append(_plain_xml(archive.read(name).decode("utf-8", "replace")))
            return "\n".join(parts)[:MAX_PREVIEW_CHARS]
    except (OSError, BadZipFile):
        return ""


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages[:8])[:MAX_PREVIEW_CHARS]
    except Exception:
        return ""


def _folder_manifest(path: Path) -> list[str]:
    items: list[str] = []
    try:
        for child in sorted(path.rglob("*"), key=lambda item: str(item).lower()):
            if len(items) >= MAX_FOLDER_ITEMS:
                break
            relative = child.relative_to(path)
            if any(part.startswith(".") for part in relative.parts):
                continue
            items.append(str(relative) + ("/" if child.is_dir() else ""))
    except (OSError, RuntimeError, ValueError):
        pass
    return items


def _normalise_one(raw: Mapping[str, Any]) -> dict[str, Any] | None:
    raw_path = str(raw.get("path") or "").strip()
    if not raw_path:
        return None
    try:
        path = Path(raw_path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    extension = path.suffix.lower()
    is_package = path.is_dir() and extension in PACKAGE_EXTENSIONS
    is_folder = path.is_dir() and not is_package
    if not path.is_file() and not path.is_dir():
        return None
    try:
        stat = path.stat()
    except OSError:
        return None
    item: dict[str, Any] = {
        "id": str(raw.get("id") or path), "path": str(path), "name": path.name,
        "kind": "folder" if is_folder else "file", "extension": extension,
        "size": int(stat.st_size), "modified_at": int(stat.st_mtime * 1000),
        "package": is_package,
    }
    if is_folder:
        item["manifest"] = _folder_manifest(path)
    elif not is_package:
        if extension in TEXT_EXTENSIONS:
            item["preview"] = _read_text(path)
        elif extension == ".docx":
            item["preview"] = _read_docx(path)
        elif extension == ".xlsx":
            item["preview"] = _read_xlsx(path)
        elif extension == ".pdf":
            item["preview"] = _read_pdf(path)
    return item


def prepare_chat_attachments(raw: Any) -> list[dict[str, Any]]:
    values: Iterable[Any] = raw if isinstance(raw, list) else []
    prepared: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in values:
        if len(prepared) >= MAX_ATTACHMENTS or not isinstance(candidate, Mapping):
            continue
        item = _normalise_one(candidate)
        if not item or item["path"] in seen:
            continue
        seen.add(item["path"])
        prepared.append(item)
    return prepared


def attachment_context_for_model(attachments: list[Mapping[str, Any]]) -> str:
    """Give models useful content without disclosing absolute local paths."""
    if not attachments:
        return ""
    public: list[dict[str, Any]] = []
    for item in attachments[:MAX_ATTACHMENTS]:
        value: dict[str, Any] = {
            "name": item.get("name"), "kind": item.get("kind"),
            "extension": item.get("extension"), "size": item.get("size"),
        }
        if item.get("preview"):
            value["content_preview"] = str(item["preview"])[:MAX_PREVIEW_CHARS]
        if item.get("manifest"):
            value["folder_manifest"] = list(item["manifest"])[:MAX_FOLDER_ITEMS]
        public.append(value)
    return "\n\nUser-selected local attachments (read-only context):\n" + json.dumps(public, ensure_ascii=False)
