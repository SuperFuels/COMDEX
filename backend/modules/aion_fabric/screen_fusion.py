from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, Iterable
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class ScreenUnderstandingFusion:
    """Fuse consented OCR, image labels, TV metadata, and live context.

    The service never receives or stores source pixels. Every conclusion names
    its evidence source and remains explicitly confidence-labelled.
    """

    _lock = threading.RLock()
    SCORE_RE = re.compile(r"\b([A-Z][A-Za-z .'-]{1,22})\s+(\d{1,3})\s*[-:]\s*(\d{1,3})\s+([A-Z][A-Za-z .'-]{1,22})\b")
    CLOCK_RE = re.compile(r"\b(?:[0-9]|[1-8][0-9]|9[0-9]):[0-5][0-9]\b")
    PRICE_RE = re.compile(r"(?:€|£|\$)\s?\d[\d,.]*|\d[\d,.]*\s?(?:€|EUR|GBP|USD)\b", re.IGNORECASE)
    INGREDIENT_TERMS = {
        "apple", "banana", "tomato", "onion", "garlic", "pepper", "salt", "flour",
        "egg", "eggs", "milk", "butter", "cheese", "chicken", "beef", "fish",
        "rice", "pasta", "potato", "potatoes", "oil", "lemon", "orange", "bread",
    }
    TECHNIQUE_TERMS = {
        "bake", "baking", "boil", "boiling", "chop", "chopping", "slice", "slicing",
        "fry", "frying", "grill", "grilling", "roast", "roasting", "mix", "mixing",
        "whisk", "whisking", "knead", "kneading", "steam", "steaming",
    }

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "perception"
        self.path = self.root / "latest_screen_fusion.json"
        self.corrections_path = self.root / "screen_corrections.json"
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _bounded_texts(perception: Dict[str, Any]) -> list[str]:
        return [" ".join(str(item).split()).strip()[:240] for item in list(perception.get("texts") or []) if str(item).strip()][:40]

    @staticmethod
    def _source(source_id: str, kind: str, detail: str, confidence: float) -> Dict[str, Any]:
        return {
            "source_id": source_id,
            "kind": kind,
            "detail": detail[:280],
            "confidence": round(max(0.0, min(float(confidence), 1.0)), 3),
        }

    @staticmethod
    def _bottom_texts(perception: Dict[str, Any]) -> list[str]:
        observations = list(perception.get("text_observations") or [])
        result = []
        for item in observations:
            if not isinstance(item, dict):
                continue
            text = " ".join(str(item.get("text") or "").split()).strip()
            y = float(item.get("y") or 0)
            x = float(item.get("x") or 0)
            width = float(item.get("width") or 0)
            center = x + (width / 2)
            if text and y <= 0.30 and 0.30 <= center <= 0.70 and len(text.split()) >= 2:
                result.append(text[:240])
        return result[:6]

    @staticmethod
    def _programme_candidates(perception: Dict[str, Any], *, surface: str, app_title: str) -> list[Dict[str, Any]]:
        media_surface = surface in {"netflix", "youtube", "media_app"} or any(
            value in app_title.lower() for value in ("netflix", "youtube", "prime", "disney", "player")
        )
        if not media_surface:
            return []
        ignored = (
            "netflix", "youtube", "search", "play", "pause", "resume", "episodes",
            "more like this", "my list", "home", "settings", "subtitles", "audio",
            "who's watching", "choose a profile", "sign in", "skip intro", "next episode",
        )
        candidates: list[Dict[str, Any]] = []
        seen: set[str] = set()
        for item in list(perception.get("text_observations") or []):
            if not isinstance(item, dict):
                continue
            text = " ".join(str(item.get("text") or "").split()).strip()[:160]
            lowered = text.lower().rstrip("?:.! ")
            confidence = float(item.get("confidence") or 0)
            height = float(item.get("height") or 0)
            width = float(item.get("width") or 0)
            if (
                not (2 <= len(text) <= 100)
                or len(text.split()) > 10
                or confidence < 0.72
                or height < 0.025
                or lowered in ignored
                or any(lowered.startswith(f"{value} ") for value in ("season", "episode", "volume"))
                or re.search(r"https?://|\b\d{1,2}:\d{2}\b|(?:€|£|\$)", text, re.I)
            ):
                continue
            key = re.sub(r"[^a-z0-9]+", " ", lowered).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            candidates.append({
                "title": text,
                "ocr_confidence": round(confidence, 3),
                "geometry_score": round(min(1.0, (height * 6) + (width * 0.15)), 3),
                "source": "owner_capture_repeated_confirmation_required",
            })
        candidates.sort(key=lambda value: (value["geometry_score"], value["ocr_confidence"]), reverse=True)
        return candidates[:5]

    def fuse(
        self,
        *,
        perception: Dict[str, Any],
        device_state: Dict[str, Any] | None = None,
        live_context: Dict[str, Any] | None = None,
        belief: Dict[str, Any] | None = None,
        provider_metadata: Dict[str, Any] | None = None,
        provider_telemetry: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        texts = self._bounded_texts(perception)
        joined = " ".join(texts)
        lowered = joined.lower()
        label_observations = [item for item in list(perception.get("labels") or []) if isinstance(item, dict)]
        labels = [str(item.get("label") or "").lower() for item in label_observations]
        inference = dict(perception.get("inference") or {})
        state = dict(device_state or {})
        app_id = str(state.get("foreground_app_id") or (live_context or {}).get("app", {}).get("id") or "unknown")[:160]
        app_title = str(state.get("foreground_app_title") or (live_context or {}).get("app", {}).get("title") or app_id)[:160]
        surface = str(inference.get("surface") or (belief or {}).get("surface") or "unknown")[:80]
        sources = [
            self._source("owner_capture", "owner_captured_phone_vision", "OCR and classifications from an explicit phone capture; source pixels deleted", float(inference.get("confidence") or 0.45)),
            self._source("tv_metadata", "webos_cached_state", f"Foreground app reported as {app_title}", 0.86 if app_id != "unknown" else 0.35),
        ]
        if live_context:
            sources.append(self._source("live_context", "explicit_live_context", "Bounded recent transcript and TV state from an explicit Pilot request", float(live_context.get("confidence") or 0.5)))
        if provider_metadata:
            metadata_kind = (
                "public_programme_catalogue"
                if str(provider_metadata.get("metadata_status") or "").startswith("public_catalogue_")
                else "official_provider_metadata"
            )
            sources.append(self._source(
                "provider_metadata",
                metadata_kind,
                f"{provider_metadata.get('provider', 'unknown')} metadata status: {provider_metadata.get('metadata_status', 'unknown')}",
                float(provider_metadata.get("metadata_confidence") or 0.3),
            ))
        if provider_telemetry:
            sources.append(self._source(
                "provider_telemetry",
                "signed_provider_adapter",
                f"Authenticated {provider_telemetry.get('provider', 'unknown')} playback telemetry",
                1.0 if provider_telemetry.get("authenticated") else 0.0,
            ))

        subtitle_candidates = self._bottom_texts(perception)
        if not subtitle_candidates and not perception.get("text_observations"):
            subtitle_candidates = [
                text for text in texts
                if 3 <= len(text.split()) <= 24
                and not any(term in text.lower() for term in ("accept all", "sign in", "search", "volume", "settings"))
            ][-3:]
        subtitles = {
            "detected": bool(subtitle_candidates),
            "lines": subtitle_candidates[:3],
            "confidence": 0.82 if self._bottom_texts(perception) else 0.48 if subtitle_candidates else 0.0,
            "source_ids": ["owner_capture"],
        }

        score = self.SCORE_RE.search(joined)
        clocks = self.CLOCK_RE.findall(joined)
        sports_terms = {"football", "soccer", "basketball", "tennis", "stadium", "scoreboard", "sports"}
        scoreboard = {
            "detected": bool(score or (clocks and sports_terms.intersection(labels + lowered.split()))),
            "score_text": score.group(0)[:160] if score else "",
            "clock": clocks[0] if clocks else "",
            "confidence": 0.92 if score else 0.68 if clocks and sports_terms.intersection(labels + lowered.split()) else 0.0,
            "source_ids": ["owner_capture"],
        }

        prices = self.PRICE_RE.findall(joined)
        product_terms = ("buy now", "add to basket", "add to cart", "product", "shop", "price", "delivery")
        products = {
            "detected": bool(prices or any(term in lowered for term in product_terms) or any(term in labels for term in ("consumer_goods", "product", "retail"))),
            "prices": prices[:5],
            "candidate_text": next((text for text in texts if any(term in text.lower() for term in product_terms)), "")[:240],
            "confidence": 0.88 if prices else 0.62 if any(term in lowered for term in product_terms) else 0.0,
            "requires_private_confirmation": True,
            "source_ids": ["owner_capture"],
        }

        location_terms = ("map", "km", "miles", "route", "near", "airport", "station", "street", "road")
        location_hits = [term for term in location_terms if re.search(rf"\b{re.escape(term)}\b", lowered)]
        locations = {
            "detected": bool(location_hits) or any(term in labels for term in ("map", "landmark", "cityscape")),
            "candidate_texts": [text for text in texts if any(re.search(rf"\b{re.escape(term)}\b", text.lower()) for term in location_terms)][:4],
            "confidence": 0.68 if location_hits else 0.5 if any(term in labels for term in ("map", "landmark", "cityscape")) else 0.0,
            "requires_private_confirmation": True,
            "source_ids": ["owner_capture"],
        }

        game_terms = ("level", "score", "health", "mission", "quest", "player", "game over", "press start")
        games = {
            "detected": surface == "games" or "game" in app_title.lower() or any(term in lowered for term in game_terms),
            "hud_texts": [text for text in texts if any(term in text.lower() for term in game_terms)][:5],
            "confidence": 0.9 if surface == "games" else 0.66 if any(term in lowered for term in game_terms) else 0.0,
            "source_ids": ["owner_capture", "tv_metadata"],
        }

        people_visible = any(term in labels for term in ("people", "person", "adult", "child"))
        ingredient_hits = sorted({
            term for term in self.INGREDIENT_TERMS
            if re.search(rf"\b{re.escape(term)}\b", lowered) or term in labels
        })
        technique_hits = sorted({
            term for term in self.TECHNIQUE_TERMS
            if re.search(rf"\b{re.escape(term)}\b", lowered) or term in labels
        })
        ignored_object_labels = {
            "people", "person", "adult", "child", "face", "text", "screen", "television",
            "indoor", "outdoor", "product", "consumer_goods", "retail",
        }
        objects = []
        for item in label_observations:
            label = " ".join(str(item.get("label") or "").split()).strip().lower()[:80]
            confidence = float(item.get("confidence") or 0)
            if label and confidence >= 0.55 and label not in ignored_object_labels and label not in objects:
                objects.append(label)
        cooking = {
            "detected": bool(ingredient_hits or technique_hits),
            "ingredients": ingredient_hits[:12],
            "techniques": technique_hits[:10],
            "confidence": 0.82 if ingredient_hits and technique_hits else 0.66 if ingredient_hits or technique_hits else 0.0,
            "source_ids": ["owner_capture"],
            "inference_limit": "Only explicitly recognized OCR terms or bounded local visual labels are reported.",
        }
        object_evidence = {
            "detected": bool(objects),
            "labels": objects[:12],
            "confidence": round(max(
                [float(item.get("confidence") or 0) for item in label_observations if str(item.get("label") or "").lower() in objects]
                or [0.0]
            ), 3),
            "source_ids": ["owner_capture"],
            "identity_inferred": False,
        }
        entities = {
            "unknown_people_visible": people_visible,
            "identity_inferred": False,
            "policy": "People remain unknown until an owner asks for an evidence-backed lookup; face identity is never guessed.",
        }
        programme_candidates = self._programme_candidates(perception, surface=surface, app_title=app_title)
        detected = [name for name, item in (("subtitles", subtitles), ("scoreboard", scoreboard), ("products", products), ("locations", locations), ("game", games), ("cooking", cooking), ("objects", object_evidence)) if item.get("detected")]
        conflict = bool(surface not in {"unknown", str(inference.get("surface") or "unknown")} and inference.get("surface") not in {None, "unknown"})
        confidence_values = [float(item.get("confidence") or 0) for item in (subtitles, scoreboard, products, locations, games, cooking, object_evidence) if item.get("detected")]
        confidence = round(sum(confidence_values) / len(confidence_values), 3) if confidence_values else round(float(inference.get("confidence") or 0.35), 3)
        summary = (
            f"Detected {', '.join(detected)} on {app_title}."
            if detected else f"The capture establishes {app_title}, but no supported live element is reliable enough yet."
        )
        record: Dict[str, Any] = {
            "schema_version": "pilot.screen-understanding.v1",
            "observation_id": f"screen_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "surface": surface,
            "app": {"id": app_id, "title": app_title},
            "summary": summary,
            "confidence": confidence,
            "source_conflict": conflict,
            "sources": sources,
            "subtitles": subtitles,
            "scoreboard": scoreboard,
            "products": products,
            "locations": locations,
            "game": games,
            "cooking": cooking,
            "objects": object_evidence,
            "entities": entities,
            "programme_candidates": programme_candidates,
            "provider_metadata": provider_metadata or None,
            "provider_telemetry": provider_telemetry or None,
            "corrections": [],
            "privacy": {
                "source_pixels_retained": False,
                "raw_audio_retained": False,
                "shared_screen_identity_resolution": False,
                "consequential_action_requires_private_confirmation": True,
            },
        }
        record["evidence_hash"] = canonical_hash(record)
        with self._lock:
            temporary = self.path.with_suffix(".tmp")
            temporary.write_bytes(canonical_bytes(record))
            os.replace(temporary, self.path)
        return record

    def correct(self, *, observation_id: str, field: str, value: str, persona_id: str) -> Dict[str, Any]:
        allowed_fields = {"subtitle", "scoreboard", "product", "location", "scene"}
        if field not in allowed_fields:
            raise ValueError("That screen correction field is not supported")
        value = " ".join(value.split()).strip()[:240]
        if len(value) < 2:
            raise ValueError("Enter a useful correction")
        with self._lock:
            current = self.latest()
            if not current or current.get("observation_id") != observation_id:
                raise ValueError("That screen observation is no longer current")
            correction = {
                "correction_id": f"correction_{uuid4().hex}",
                "field": field,
                "value": value,
                "persona_id": persona_id,
                "created_at": utc_now_iso(),
            }
            current["corrections"] = [*list(current.get("corrections") or []), correction][-20:]
            current["corrected_by_owner"] = True
            current["evidence_hash"] = canonical_hash({key: item for key, item in current.items() if key != "evidence_hash"})
            temporary = self.path.with_suffix(".tmp")
            temporary.write_bytes(canonical_bytes(current))
            os.replace(temporary, self.path)
            return current

    def latest(self) -> Dict[str, Any] | None:
        with self._lock:
            if not self.path.exists():
                return None
            try:
                value = json.loads(self.path.read_text(encoding="utf-8"))
                return value if isinstance(value, dict) else None
            except (OSError, json.JSONDecodeError):
                return None
