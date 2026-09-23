from __future__ import annotations

import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class EvidenceBackedProgrammeCompanion:
    """Answer cast questions from a verified programme record without face guessing."""

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "live"
        self.path = self.root / "latest_programme_companion.json"
        self.cache_path = self.root / "programme_cast_cache.json"
        self.credits_cache_path = self.root / "programme_person_credits_cache.json"
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _normalise(value: Any) -> str:
        text = unicodedata.normalize("NFKD", str(value or ""))
        text = "".join(character for character in text if not unicodedata.combining(character))
        return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

    @staticmethod
    def _fetch_json(url: str) -> Any:
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "Pilot-Fabric/0.47.0 programme-companion"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = response.read(500_001)
        if len(payload) > 500_000:
            raise RuntimeError("Programme cast response exceeded its safety limit")
        return json.loads(payload)

    def _read_cache(self) -> Dict[str, Any]:
        try:
            value = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_cache(self, value: Dict[str, Any]) -> None:
        temporary = self.cache_path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(value))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.cache_path)

    def _read_credits_cache(self) -> Dict[str, Any]:
        try:
            value = json.loads(self.credits_cache_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_credits_cache(self, value: Dict[str, Any]) -> None:
        temporary = self.credits_cache_path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(value))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.credits_cache_path)

    def _show_id(self, *, title: str, provider_metadata: Dict[str, Any]) -> tuple[str | None, str]:
        if (
            provider_metadata.get("metadata_status") == "public_catalogue_exact_match"
            and str(provider_metadata.get("content_id") or "").isdigit()
        ):
            return str(provider_metadata["content_id"]), "existing_exact_catalogue_identity"
        payload = self._fetch_json(
            "https://api.tvmaze.com/search/shows?" + urllib.parse.urlencode({"q": title})
        )
        exact: Dict[str, str] = {}
        for row in list(payload or [])[:10] if isinstance(payload, list) else []:
            show = dict(row.get("show") or {}) if isinstance(row, dict) else {}
            show_id = str(show.get("id") or "")
            name = " ".join(str(show.get("name") or "").split()).strip()
            if show_id.isdigit() and self._normalise(name) == self._normalise(title):
                exact[show_id] = name
        if len(exact) != 1:
            return None, "ambiguous_or_missing_exact_catalogue_identity"
        return next(iter(exact)), "new_exact_catalogue_identity"

    def _cast(self, show_id: str) -> tuple[list[Dict[str, Any]], bool]:
        cache = self._read_cache()
        entries = dict(cache.get("entries") or {})
        cached = dict(entries.get(show_id) or {})
        if cached and time.time() - float(cached.get("cached_at_epoch") or 0) < 86_400:
            return list(cached.get("cast") or []), True
        payload = self._fetch_json(f"https://api.tvmaze.com/shows/{show_id}/cast")
        cast: list[Dict[str, Any]] = []
        for row in list(payload or [])[:40] if isinstance(payload, list) else []:
            person = dict(row.get("person") or {}) if isinstance(row, dict) else {}
            character = dict(row.get("character") or {}) if isinstance(row, dict) else {}
            person_name = " ".join(str(person.get("name") or "").split()).strip()[:160]
            character_name = " ".join(str(character.get("name") or "").split()).strip()[:160]
            if not person_name:
                continue
            cast.append({
                "person_id": str(person.get("id") or "")[:40] or None,
                "person": person_name,
                "character": character_name or "Character not listed",
                "person_url": str(person.get("url") or "")[:500] or None,
                "character_url": str(character.get("url") or "")[:500] or None,
            })
            if len(cast) >= 20:
                break
        entries[show_id] = {"cached_at_epoch": time.time(), "cast": cast}
        if len(entries) > 50:
            entries = dict(sorted(
                entries.items(),
                key=lambda item: float((item[1] or {}).get("cached_at_epoch") or 0),
                reverse=True,
            )[:50])
        self._write_cache({"schema_version": "pilot.programme-cast-cache.v1", "entries": entries})
        return cast, False

    def _person_credits(self, person_id: str) -> tuple[list[Dict[str, Any]], bool]:
        cache = self._read_credits_cache()
        entries = dict(cache.get("entries") or {})
        cached = dict(entries.get(person_id) or {})
        if cached and time.time() - float(cached.get("cached_at_epoch") or 0) < 86_400:
            return list(cached.get("credits") or []), True
        payload = self._fetch_json(
            f"https://api.tvmaze.com/people/{person_id}/castcredits?embed=show"
        )
        credits: list[Dict[str, Any]] = []
        seen: set[str] = set()
        for row in list(payload or [])[:80] if isinstance(payload, list) else []:
            embedded = dict(row.get("_embedded") or {}) if isinstance(row, dict) else {}
            show = dict(embedded.get("show") or {})
            show_id = str(show.get("id") or "")[:40]
            title = " ".join(str(show.get("name") or "").split()).strip()[:160]
            if not title or show_id in seen:
                continue
            seen.add(show_id)
            credits.append({
                "catalogue_id": show_id or None,
                "title": title,
                "premiered": str(show.get("premiered") or "")[:20] or None,
                "ended": str(show.get("ended") or "")[:20] or None,
                "type": str(show.get("type") or "")[:60] or None,
                "official_url": str(show.get("url") or "")[:500] or None,
            })
            if len(credits) >= 30:
                break
        entries[person_id] = {"cached_at_epoch": time.time(), "credits": credits}
        if len(entries) > 100:
            entries = dict(sorted(
                entries.items(),
                key=lambda item: float((item[1] or {}).get("cached_at_epoch") or 0),
                reverse=True,
            )[:100])
        self._write_credits_cache({"schema_version": "pilot.person-credits-cache.v1", "entries": entries})
        return credits, False

    def lookup(
        self,
        *,
        programme: Dict[str, Any] | None,
        provider_metadata: Dict[str, Any] | None,
        question_kind: str = "cast",
        character: str = "",
        person: str = "",
    ) -> Dict[str, Any]:
        programme = dict(programme or {})
        provider_metadata = dict(provider_metadata or {})
        title = " ".join(str(programme.get("title") or provider_metadata.get("title") or "").split()).strip()[:200]
        stable = bool(programme.get("stable") or provider_metadata.get("catalogue_identity_verified"))
        cast: list[Dict[str, Any]] = []
        show_id = None
        identity_route = "programme_identity_missing"
        cache_hit = False
        error = None
        if title and stable:
            try:
                show_id, identity_route = self._show_id(title=title, provider_metadata=provider_metadata)
                if show_id:
                    cast, cache_hit = self._cast(show_id)
            except Exception as exc:
                error = type(exc).__name__
                identity_route = "public_cast_evidence_unavailable"

        requested_character = " ".join(str(character or "").split()).strip()[:160]
        requested_person = " ".join(str(person or "").split()).strip()[:160]
        matches = []
        if requested_character:
            key = self._normalise(requested_character)
            matches = [item for item in cast if self._normalise(item.get("character")) == key]
        person_matches = []
        credits: list[Dict[str, Any]] = []
        credits_cache_hit = False
        if requested_person:
            key = self._normalise(requested_person)
            person_matches = [item for item in cast if self._normalise(item.get("person")) == key]
            if len(person_matches) == 1 and str(person_matches[0].get("person_id") or "").isdigit():
                try:
                    credits, credits_cache_hit = self._person_credits(str(person_matches[0]["person_id"]))
                except Exception as exc:
                    error = type(exc).__name__

        if not title or not stable:
            answer = "I do not yet have a stable programme identity. Capture the programme screen twice, then ask again."
            confidence = 0.0
        elif not show_id:
            answer = f"I could not establish one exact public catalogue record for {title}, so I will not guess its cast."
            confidence = 0.0
        elif requested_person and len(person_matches) == 1 and credits:
            other = [item for item in credits if self._normalise(item.get("title")) != self._normalise(title)]
            names = ", ".join(str(item["title"]) for item in other[:5])
            answer = (
                f"Verified credits for {person_matches[0]['person']} beyond {title} include {names}."
                if names else f"I verified {person_matches[0]['person']} in {title}, but found no other show credits in this source."
            )
            confidence = 0.94 if names else 0.45
        elif requested_person:
            answer = f"I could not match {requested_person} to exactly one verified cast member in {title}, so I will not guess their credits."
            confidence = 0.0
        elif requested_character and matches:
            item = matches[0]
            answer = f"In {title}, {item['character']} is played by {item['person']}."
            confidence = 0.96
        elif requested_character:
            answer = f"I could not verify who plays {requested_character} in the main cast record for {title}."
            confidence = 0.35
        elif cast:
            leading = ", ".join(f"{item['person']} as {item['character']}" for item in cast[:4])
            prefix = "I cannot identify the person currently visible. " if question_kind == "visible_actor" else ""
            answer = f"{prefix}The verified main cast for {title} includes {leading}."
            confidence = 0.92
        else:
            answer = f"I verified {title}, but its public main-cast record is empty or unavailable."
            confidence = 0.2

        record: Dict[str, Any] = {
            "schema_version": "pilot.programme-companion.v1",
            "lookup_id": f"cast_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "programme": {"title": title or None, "stable": stable, "catalogue_id": show_id},
            "question_kind": question_kind,
            "requested_character": requested_character or None,
            "requested_person": requested_person or None,
            "answer": answer,
            "cast": cast[:12],
            "matches": matches[:5],
            "person_matches": person_matches[:3],
            "credits": credits[:20],
            "identity_route": identity_route,
            "confidence": round(confidence, 3),
            "catalogue_cache_hit": cache_hit,
            "credits_cache_hit": credits_cache_hit,
            "catalogue_error": error,
            "source": {
                "provider": "TVmaze",
                "url": f"https://api.tvmaze.com/shows/{show_id}/cast" if show_id else "https://www.tvmaze.com/api",
                "attribution": "Cast data: TVmaze (CC BY-SA)",
            },
            "safety": {
                "face_recognition_used": False,
                "visible_person_identified": False,
                "cast_members_are_not_claimed_visible": True,
                "current_playback_verified": bool(programme.get("current_playback_verified")),
                "protected_media_copied": False,
            },
            "presentation": {"playback_preserved": True, "spoken_summary": True, "private_phone_detail": True},
        }
        record["evidence_hash"] = canonical_hash({
            "programme": record["programme"],
            "cast": record["cast"],
            "credits": record["credits"],
            "identity_route": identity_route,
        })
        record["record_hash"] = canonical_hash(record)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(record))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)
        return record

    def latest(self) -> Dict[str, Any] | None:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None
