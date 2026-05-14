# /workspaces/COMDEX/backend/modules/aion_equities/openai_operating_brief_store.py
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_segment(value: str) -> str:
    return str(value).replace("/", "_").replace("\\", "_").replace(":", "-").strip()


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def _default_storage_dir() -> Path:
    return Path(__file__).resolve().parent / "data" / "openai_operating_briefs"


def operating_brief_storage_path(brief_id: str, *, base_dir: Optional[Path] = None) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    return root / f"{_safe_segment(brief_id)}.json"


def active_brief_pointer_path(*, base_dir: Optional[Path] = None) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    return root / "_active_brief.json"


def _normalize_sections(sections: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in sections or []:
        if isinstance(item, dict):
            out.append(deepcopy(item))
    return out


def _sections_to_brief_text(sections: List[Dict[str, Any]]) -> str:
    """
    Stable single-string representation used for prompt injection.

    Preference per section:
      - content
      - body
      - text
    """
    parts: List[str] = []
    for s in sections or []:
        if not isinstance(s, dict):
            continue

        chunk = (
            s.get("content")
            if s.get("content") is not None
            else s.get("body")
            if s.get("body") is not None
            else s.get("text")
        )
        chunk_s = str(chunk or "").strip()
        if not chunk_s:
            continue

        title = str(s.get("title") or "").strip()
        if title:
            parts.append(f"# {title}\n{chunk_s}")
        else:
            parts.append(chunk_s)

    return "\n\n".join(parts).strip()


def _normalize_text_to_summary_and_sections(
    *,
    text: str,
    summary: Optional[str] = None,
    sections: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    clean_text = str(text or "").strip()
    clean_sections = _normalize_sections(sections)

    # If sections provided, respect them.
    if clean_sections:
        resolved_summary = str(summary or "").strip()
        if not resolved_summary:
            resolved_summary = str(
                clean_sections[0].get("content")
                or clean_sections[0].get("body")
                or clean_sections[0].get("text")
                or ""
            ).strip()
        if not resolved_summary:
            resolved_summary = clean_text[:240] if clean_text else ""
        return resolved_summary, clean_sections

    # If text provided, wrap into one section.
    if clean_text:
        first_line = next((line.strip() for line in clean_text.splitlines() if line.strip()), "")
        resolved_summary = str(summary or first_line or clean_text[:240]).strip()
        return (
            resolved_summary,
            [
                {
                    "section_id": "operating_brief_main",
                    "title": "Operating Brief",
                    "content": clean_text,
                }
            ],
        )

    resolved_summary = str(summary or "").strip()
    return resolved_summary, clean_sections


def build_operating_brief_payload(
    *,
    brief_id: str,
    version: str,
    title: str,
    summary: Optional[str] = None,
    sections: Optional[List[Dict[str, Any]]] = None,
    brief_text: Optional[str] = None,
    content: Optional[str] = None,
    body: Optional[str] = None,
    generated_by: str = "aion_equities.openai_operating_brief_store",
    payload_patch: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Contract:
      - persist BOTH:
          - sections[] (structured)
          - brief_text (single string) derived from sections for prompt injection
    """
    now = _utc_now_iso()

    text = str(brief_text or content or body or "").strip()
    normalized_summary, normalized_sections = _normalize_text_to_summary_and_sections(
        text=text,
        summary=summary,
        sections=sections,
    )
    normalized_sections = _normalize_sections(normalized_sections)

    # If caller provided ONLY raw text and no explicit sections, the above created a section.
    # Always derive brief_text from sections to keep them in sync.
    resolved_brief_text = _sections_to_brief_text(normalized_sections)

    payload: Dict[str, Any] = {
        "brief_id": str(brief_id),
        "version": str(version),
        "title": str(title),
        "summary": str(normalized_summary or ""),
        "sections": deepcopy(normalized_sections),
        "brief_text": str(resolved_brief_text),
        "status": "active",
        "generated_by": str(generated_by),
        "created_at": now,
        "updated_at": now,
    }

    if payload_patch:
        payload = _deep_merge(payload, payload_patch)

    # final normalize
    payload["brief_id"] = str(payload.get("brief_id") or "")
    payload["version"] = str(payload.get("version") or "")
    payload["title"] = str(payload.get("title") or "")
    payload["summary"] = str(payload.get("summary") or "")
    payload["sections"] = _normalize_sections(payload.get("sections"))
    payload["brief_text"] = str(payload.get("brief_text") or _sections_to_brief_text(payload["sections"])).strip()
    payload["updated_at"] = _utc_now_iso()

    return payload


def save_operating_brief_payload(payload: Dict[str, Any], *, base_dir: Optional[Path] = None) -> Path:
    path = operating_brief_storage_path(str(payload["brief_id"]), base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_operating_brief_payload(brief_id: str, *, base_dir: Optional[Path] = None) -> Dict[str, Any]:
    path = operating_brief_storage_path(brief_id, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"OpenAI operating brief not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))

    # Back-compat: older briefs may not have brief_text
    if not str(payload.get("brief_text") or "").strip():
        sections = payload.get("sections") or []
        payload["brief_text"] = _sections_to_brief_text(_normalize_sections(sections)) if isinstance(sections, list) else ""

    # Also sanitize sections
    payload["sections"] = _normalize_sections(payload.get("sections"))

    return payload


class OpenAIOperatingBriefStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "openai_operating_briefs"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, brief_id: str) -> Path:
        return operating_brief_storage_path(brief_id, base_dir=self.base_dir)

    def pointer_path(self) -> Path:
        return active_brief_pointer_path(base_dir=self.base_dir)

    def save_operating_brief(
        self,
        *,
        brief_id: str,
        version: str,
        title: str,
        summary: Optional[str] = None,
        sections: Optional[List[Dict[str, Any]]] = None,
        content: Optional[str] = None,
        body: Optional[str] = None,
        brief_text: Optional[str] = None,
        generated_by: str = "aion_equities.openai_operating_brief_store",
        payload_patch: Optional[Dict[str, Any]] = None,
        set_active: bool = True,
        **_: Any,
    ) -> Dict[str, Any]:
        text = str(brief_text or content or body or "").strip()

        if not text and not sections:
            raise TypeError("save_operating_brief() requires sections or brief_text/content/body.")

        payload = build_operating_brief_payload(
            brief_id=brief_id,
            version=version,
            title=title,
            summary=summary,
            sections=sections,
            brief_text=text,
            generated_by=generated_by,
            payload_patch=payload_patch,
        )
        save_operating_brief_payload(payload, base_dir=self.base_dir)

        if set_active:
            self.set_active_brief(payload["brief_id"])

        return payload

    def load_operating_brief(self, brief_id: str) -> Dict[str, Any]:
        return load_operating_brief_payload(brief_id, base_dir=self.base_dir)

    def set_active_brief(self, brief_id: str) -> Dict[str, Any]:
        payload = self.load_operating_brief(brief_id)
        pointer = {
            "brief_id": payload["brief_id"],
            "version": payload.get("version"),
            "updated_at": _utc_now_iso(),
        }
        self.pointer_path().write_text(json.dumps(pointer, ensure_ascii=False, indent=2), encoding="utf-8")
        return pointer

    def load_active_brief(self) -> Dict[str, Any]:
        ptr = self.pointer_path()
        if not ptr.exists():
            raise FileNotFoundError(f"Active operating brief pointer not found: {ptr}")
        pointer = json.loads(ptr.read_text(encoding="utf-8"))
        brief_id = pointer.get("brief_id")
        if not brief_id:
            raise ValueError("Active operating brief pointer missing brief_id")
        return self.load_operating_brief(str(brief_id))

    def operating_brief_exists(self, brief_id: str) -> bool:
        return self.storage_path(brief_id).exists()

    def list_brief_ids(self) -> List[str]:
        out: List[str] = []
        for path in sorted(self.base_dir.glob("*.json")):
            if path.name == "_active_brief.json":
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            brief_id = payload.get("brief_id")
            if isinstance(brief_id, str) and brief_id.strip():
                out.append(brief_id.strip())
            else:
                out.append(path.stem.replace("_", "/"))
        return out

    def backfill_brief_text(self, brief_id: str) -> Dict[str, Any]:
        payload = self.load_operating_brief(brief_id)
        payload["sections"] = _normalize_sections(payload.get("sections"))
        payload["brief_text"] = _sections_to_brief_text(payload["sections"])
        save_operating_brief_payload(payload, base_dir=self.base_dir)
        return payload


__all__ = [
    "build_operating_brief_payload",
    "save_operating_brief_payload",
    "load_operating_brief_payload",
    "OpenAIOperatingBriefStore",
]