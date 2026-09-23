from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class PrivateProgrammeSaves:
    """Prepare shared-TV evidence, then bind it only after private persona claim."""

    CATEGORIES = {"product", "recipe", "destination", "music", "learning", "idea"}

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "private_saves"
        self.pending_path = self.root / "pending.json"
        self.saved_path = self.root / "saved.json"
        self.deleted_path = self.root / "deleted.json"
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _read(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value
        except (OSError, json.JSONDecodeError):
            return default

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(value))
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _bounded_lines(live_context: Dict[str, Any], screen: Dict[str, Any]) -> list[str]:
        values = [str(value) for value in list(live_context.get("recent_transcripts") or [])[-4:]]
        values.extend(str(value) for value in list((screen.get("subtitles") or {}).get("lines") or [])[-3:])
        return [" ".join(value.split())[:360] for value in values if value.strip()][-6:]

    @classmethod
    def _candidate(
        cls,
        category: str,
        *,
        live_context: Dict[str, Any],
        screen: Dict[str, Any],
        provider: Dict[str, Any],
    ) -> tuple[str, str, list[Dict[str, Any]], float]:
        lines = cls._bounded_lines(live_context, screen)
        evidence: list[Dict[str, Any]] = []
        for line in lines:
            evidence.append({"kind": "local_dialogue_or_captured_subtitle", "detail": line})
        if category == "product":
            finding = dict(screen.get("products") or {})
            title = str(finding.get("candidate_text") or provider.get("title") or "Product seen on television")[:240]
            detail = " · ".join(str(value) for value in list(finding.get("prices") or [])[:5]) or (lines[-1] if lines else "No reliable price captured")
            confidence = float(finding.get("confidence") or 0.35)
            evidence.append({"kind": "owner_captured_product", "detail": detail[:360]})
        elif category == "destination":
            finding = dict(screen.get("locations") or {})
            candidates = list(finding.get("candidate_texts") or [])
            title = str(candidates[0] if candidates else provider.get("title") or "Destination seen on television")[:240]
            detail = lines[-1] if lines else "Location requires later private research"
            confidence = float(finding.get("confidence") or 0.35)
            evidence.append({"kind": "owner_captured_location", "detail": title})
        elif category == "music":
            title = str(provider.get("title") or (lines[-1] if lines else "Music heard on television"))[:240]
            detail = str(provider.get("provider") or "Provider not established")[:160]
            confidence = float(provider.get("metadata_confidence") or 0.35)
            evidence.append({"kind": "provider_metadata", "detail": detail})
        elif category == "recipe":
            ingredient_line = next((line for line in reversed(lines) if re.search(r"\b(add|mix|cook|bake|ingredient|tablespoon|grams?|cup)\b", line, re.I)), "")
            title = str(provider.get("title") or "Recipe seen on television")[:240]
            detail = ingredient_line or (lines[-1] if lines else "Recipe details were not reliably captured")
            confidence = 0.68 if ingredient_line else 0.35
        elif category == "learning":
            title = str(provider.get("title") or "Learning concept from television")[:240]
            detail = lines[-1] if lines else "Concept requires another screen observation"
            confidence = 0.58 if lines else 0.25
        else:
            title = "Idea from television"
            detail = lines[-1] if lines else str((screen.get("summary") or "Idea requires another screen observation"))[:360]
            confidence = 0.55 if lines or screen.get("summary") else 0.2
        official_url = str(provider.get("official_url") or "")
        if official_url.startswith("https://"):
            evidence.append({"kind": "official_provider_link", "detail": official_url[:1000]})
        return title, detail[:500], evidence[:8], round(max(0.0, min(confidence, 1.0)), 3)

    def prepare(
        self,
        *,
        category: str,
        request: str,
        live_context: Dict[str, Any],
        screen_understanding: Dict[str, Any] | None,
        provider_metadata: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        if category not in self.CATEGORIES:
            raise ValueError("Unsupported private-save category")
        screen, provider = dict(screen_understanding or {}), dict(provider_metadata or {})
        title, detail, evidence, confidence = self._candidate(
            category, live_context=live_context, screen=screen, provider=provider
        )
        item: Dict[str, Any] = {
            "schema_version": "pilot.private-save.v1",
            "save_id": f"save_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "expires_at": (self._now() + timedelta(minutes=30)).isoformat(timespec="seconds"),
            "category": category,
            "request": " ".join(request.split())[:300],
            "title": title,
            "detail": detail,
            "evidence": evidence,
            "confidence": confidence,
            "status": "awaiting_private_claim",
            "persona_id": None,
            "privacy": {
                "shared_tv_selected_persona": False,
                "private_claim_required": True,
                "purchase_executed": False,
                "message_sent": False,
                "raw_audio_retained": False,
                "source_pixels_retained": False,
            },
        }
        item["evidence_hash"] = canonical_hash({"context": live_context.get("context_hash"), "evidence": evidence})
        item["item_hash"] = canonical_hash(item)
        self._write(self.pending_path, item)
        return item

    def pending(self) -> Dict[str, Any] | None:
        value = self._read(self.pending_path, None)
        if not isinstance(value, dict):
            return None
        try:
            expires = datetime.fromisoformat(
                str(value.get("expires_at") or "1970-01-01T00:00:00+00:00").replace("Z", "+00:00")
            )
        except ValueError:
            expires = datetime.fromtimestamp(0, timezone.utc)
        if expires <= self._now() and value.get("status") == "awaiting_private_claim":
            value["status"] = "expired"
            self._write(self.pending_path, value)
        return value

    def claim(self, save_id: str, *, persona_id: str) -> Dict[str, Any]:
        item = self.pending()
        if not item or item.get("save_id") != save_id:
            raise KeyError("That private save is no longer current")
        if item.get("status") == "expired":
            raise PermissionError("That private save has expired")
        if item.get("status") == "saved":
            if item.get("persona_id") != persona_id:
                raise PermissionError("That item belongs to another private identity")
            return dict(item)
        if item.get("status") != "awaiting_private_claim":
            raise PermissionError("That item cannot be saved")
        item["persona_id"] = persona_id
        item["status"] = "saved"
        item["saved_at"] = utc_now_iso()
        item["item_hash"] = canonical_hash({key: value for key, value in item.items() if key != "item_hash"})
        saved = [dict(value) for value in self._read(self.saved_path, []) if isinstance(value, dict)]
        duplicate = next((value for value in saved if value.get("persona_id") == persona_id and value.get("evidence_hash") == item.get("evidence_hash") and value.get("category") == item.get("category")), None)
        if duplicate:
            item = duplicate
        else:
            saved = saved[-199:] + [item]
            self._write(self.saved_path, saved)
        self._write(self.pending_path, item)
        return dict(item)

    def delete(self, save_id: str, *, persona_id: str, idempotency_key: str | None = None) -> Dict[str, Any]:
        saved = [dict(value) for value in self._read(self.saved_path, []) if isinstance(value, dict)]
        target = next((value for value in saved if value.get("save_id") == save_id), None)
        if target is None:
            deleted = [dict(value) for value in self._read(self.deleted_path, []) if isinstance(value, dict)]
            previous = next((value for value in deleted if value.get("save_id") == save_id and value.get("persona_id") == persona_id and value.get("idempotency_key") == idempotency_key), None)
            if previous:
                return dict(previous)
            raise KeyError("Saved item was not found")
        if target.get("persona_id") != persona_id:
            raise PermissionError("Only the owning private identity may delete this item")
        saved = [value for value in saved if value.get("save_id") != save_id]
        self._write(self.saved_path, saved)
        receipt = {"save_id": save_id, "persona_id": persona_id, "status": "deleted", "deleted_at": utc_now_iso(), "idempotency_key": str(idempotency_key or "")[:160] or None}
        deleted = [dict(value) for value in self._read(self.deleted_path, []) if isinstance(value, dict)][-199:] + [receipt]
        self._write(self.deleted_path, deleted)
        return receipt

    def get_saved(self, save_id: str, *, persona_id: str) -> Dict[str, Any]:
        saved = [dict(value) for value in self._read(self.saved_path, []) if isinstance(value, dict)]
        target = next((value for value in saved if value.get("save_id") == save_id), None)
        if target is None:
            raise KeyError("Saved item was not found")
        if target.get("persona_id") != persona_id:
            raise PermissionError("That saved item belongs to another private identity")
        return dict(target)

    def snapshot(self, *, persona_id: str | None = None) -> Dict[str, Any]:
        saved = [dict(value) for value in self._read(self.saved_path, []) if isinstance(value, dict)]
        if persona_id:
            saved = [value for value in saved if value.get("persona_id") == persona_id]
        pending = self.pending()
        if persona_id and pending and pending.get("persona_id") not in {None, persona_id}:
            pending = None
        return {"pending": pending, "saved": saved[-50:], "saved_count": len(saved)}
