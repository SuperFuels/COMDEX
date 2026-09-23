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


class ProgrammeOriginEvidence:
    """Resolve structured locations and source works without plot or face inference."""

    PROPERTIES = {
        "P915": "filming_locations",
        "P840": "narrative_locations",
        "P144": "based_on",
        "P495": "countries_of_origin",
        "P364": "original_languages",
        "P449": "original_broadcasters",
    }

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "live"
        self.path = self.root / "latest_programme_origins.json"
        self.cache_path = self.root / "programme_origins_cache.json"
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
            headers={"Accept": "application/json", "User-Agent": "Pilot-Fabric/0.47.0 programme-origins"},
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = response.read(750_001)
        if len(payload) > 750_000:
            raise RuntimeError("Programme origin response exceeded its safety limit")
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

    @classmethod
    def _entity_ids(cls, entity: Dict[str, Any], property_id: str) -> list[str]:
        result: list[str] = []
        for statement in list((entity.get("claims") or {}).get(property_id) or [])[:20]:
            value = (((statement.get("mainsnak") or {}).get("datavalue") or {}).get("value")) if isinstance(statement, dict) else None
            entity_id = str((value or {}).get("id") or "") if isinstance(value, dict) else ""
            if re.fullmatch(r"Q\d+", entity_id) and entity_id not in result:
                result.append(entity_id)
        return result

    def _labels(self, ids: list[str]) -> Dict[str, str]:
        if not ids:
            return {}
        url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
            "action": "wbgetentities",
            "ids": "|".join(ids[:50]),
            "props": "labels",
            "languages": "en",
            "format": "json",
            "origin": "*",
        })
        payload = self._fetch_json(url)
        result: Dict[str, str] = {}
        for entity_id, entity in dict(payload.get("entities") or {}).items():
            label = str(((entity.get("labels") or {}).get("en") or {}).get("value") or "").strip()[:160]
            if label:
                result[str(entity_id)] = label
        return result

    def _resolve(self, title: str) -> Dict[str, Any]:
        search_url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
            "action": "wbsearchentities",
            "search": title,
            "language": "en",
            "uselang": "en",
            "type": "item",
            "limit": 8,
            "format": "json",
            "origin": "*",
        })
        payload = self._fetch_json(search_url)
        media_terms = ("television", "tv series", "film", "movie", "programme", "program", "miniseries")
        exact = []
        for item in list(payload.get("search") or [])[:8]:
            label = " ".join(str(item.get("label") or "").split()).strip()
            description = " ".join(str(item.get("description") or "").split()).strip().lower()
            entity_id = str(item.get("id") or "")
            if self._normalise(label) == self._normalise(title) and re.fullmatch(r"Q\d+", entity_id) and any(term in description for term in media_terms):
                exact.append({"entity_id": entity_id, "label": label, "description": description})
        if len(exact) != 1:
            return {"status": "ambiguous_or_missing_exact_media_entity", "candidates": exact[:5]}
        match = exact[0]
        entity_payload = self._fetch_json(
            f"https://www.wikidata.org/wiki/Special:EntityData/{match['entity_id']}.json"
        )
        entity = dict((entity_payload.get("entities") or {}).get(match["entity_id"]) or {})
        ids_by_field = {
            field: self._entity_ids(entity, property_id)
            for property_id, field in self.PROPERTIES.items()
        }
        all_ids = []
        for values in ids_by_field.values():
            for entity_id in values:
                if entity_id not in all_ids:
                    all_ids.append(entity_id)
        labels = self._labels(all_ids)
        return {
            "status": "exact_structured_entity",
            "entity_id": match["entity_id"],
            "entity_label": match["label"],
            "entity_description": match["description"][:240],
            **{
                field: [{"entity_id": value, "label": labels.get(value, value)} for value in values]
                for field, values in ids_by_field.items()
            },
        }

    def lookup(self, *, programme: Dict[str, Any] | None, question_kind: str) -> Dict[str, Any]:
        programme = dict(programme or {})
        title = " ".join(str(programme.get("title") or "").split()).strip()[:200]
        stable = bool(programme.get("stable"))
        cache_hit = False
        evidence: Dict[str, Any] = {"status": "programme_identity_missing"}
        error = None
        if title and stable:
            key = canonical_hash({"title": self._normalise(title), "source": "wikidata"})
            cache = self._read_cache()
            entries = dict(cache.get("entries") or {})
            cached = dict(entries.get(key) or {})
            if cached and time.time() - float(cached.get("cached_at_epoch") or 0) < 86_400:
                evidence = dict(cached.get("evidence") or {})
                cache_hit = True
            else:
                try:
                    evidence = self._resolve(title)
                except Exception as exc:
                    error = type(exc).__name__
                    evidence = {"status": "structured_public_evidence_unavailable"}
                entries[key] = {"cached_at_epoch": time.time(), "evidence": evidence}
                if len(entries) > 100:
                    entries = dict(sorted(
                        entries.items(),
                        key=lambda item: float((item[1] or {}).get("cached_at_epoch") or 0),
                        reverse=True,
                    )[:100])
                self._write_cache({"schema_version": "pilot.programme-origins-cache.v1", "entries": entries})

        if not title or not stable:
            answer = "I do not yet have a stable programme identity. Capture the programme screen twice, then ask again."
            confidence = 0.0
        elif evidence.get("status") != "exact_structured_entity":
            answer = f"I could not establish one exact structured source record for {title}, so I will not guess."
            confidence = 0.0
        elif question_kind == "filming_location":
            values = [str(item["label"]) for item in evidence.get("filming_locations") or []]
            answer = f"The structured source lists these filming locations for {title}: {', '.join(values)}." if values else f"The exact source record for {title} does not list a filming location."
            confidence = 0.93 if values else 0.45
        elif question_kind == "setting":
            values = [str(item["label"]) for item in evidence.get("narrative_locations") or []]
            answer = f"The structured source lists the setting for {title} as {', '.join(values)}." if values else f"The exact source record for {title} does not list a narrative location."
            confidence = 0.93 if values else 0.45
        elif question_kind == "original_source":
            values = [str(item["label"]) for item in evidence.get("based_on") or []]
            answer = f"The structured source says {title} is based on {', '.join(values)}." if values else f"The exact source record for {title} does not identify an original source work."
            confidence = 0.93 if values else 0.45
        else:
            answer = f"I found the exact structured programme record for {title}."
            confidence = 0.8

        record: Dict[str, Any] = {
            "schema_version": "pilot.programme-origins.v1",
            "lookup_id": f"origin_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "programme": {"title": title or None, "stable": stable},
            "question_kind": question_kind,
            "answer": answer,
            "confidence": round(confidence, 3),
            "evidence": evidence,
            "cache_hit": cache_hit,
            "source_error": error,
            "source": {
                "provider": "Wikidata",
                "url": f"https://www.wikidata.org/wiki/{evidence.get('entity_id')}" if evidence.get("entity_id") else "https://www.wikidata.org/wiki/Help:Data_access",
                "license": "CC0",
            },
            "safety": {
                "face_recognition_used": False,
                "plot_inference_used": False,
                "current_scene_location_claimed": False,
                "protected_media_copied": False,
            },
            "presentation": {"playback_preserved": True, "spoken_summary": True, "private_phone_detail": True},
        }
        record["evidence_hash"] = canonical_hash({"programme": record["programme"], "evidence": evidence})
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
