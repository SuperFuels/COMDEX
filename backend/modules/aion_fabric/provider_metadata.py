from __future__ import annotations

import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class ProviderMetadataResolver:
    """Normalize official provider identifiers without inferring entitlement."""

    YOUTUBE_ID = re.compile(r"(?:youtu\.be/|youtube\.com/(?:watch\?[^ ]*v=|shorts/|embed/))([A-Za-z0-9_-]{11})", re.I)
    NETFLIX_ID = re.compile(r"netflix\.com/(?:[a-z]{2}(?:-[a-z]{2})?/)?title/(\d{5,10})", re.I)
    TWITCH_CLIP = re.compile(r"(?:clips\.twitch\.tv/|twitch\.tv/[^/]+/clip/)([A-Za-z0-9_-]+)", re.I)

    def __init__(self, runtime_dir: str | Path) -> None:
        self.path = Path(runtime_dir) / "perception" / "latest_provider_metadata.json"
        self.catalogue_cache_path = Path(runtime_dir) / "perception" / "programme_catalogue_cache.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _normalise_title(value: Any) -> str:
        text = unicodedata.normalize("NFKD", str(value or ""))
        text = "".join(character for character in text if not unicodedata.combining(character))
        return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

    @classmethod
    def _title_candidates(cls, values: Iterable[Any]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = " ".join(str(value or "").split()).strip()[:160]
            key = cls._normalise_title(text)
            if not (2 <= len(key) <= 120) or key in seen:
                continue
            seen.add(key)
            result.append(text)
        return result[:5]

    def _read_catalogue_cache(self) -> Dict[str, Any]:
        try:
            value = json.loads(self.catalogue_cache_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_catalogue_cache(self, value: Dict[str, Any]) -> None:
        temporary = self.catalogue_cache_path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(value))
        os.replace(temporary, self.catalogue_cache_path)

    @staticmethod
    def _fetch_json(url: str, *, headers: Dict[str, str] | None = None) -> Any:
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "Pilot-Fabric/0.47.0 programme-identity", **(headers or {})},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = response.read(500_001)
        if len(payload) > 500_000:
            raise RuntimeError("Programme catalogue response exceeded its safety limit")
        return json.loads(payload)

    def _public_catalogue(self, candidates: Iterable[Any]) -> Dict[str, Any] | None:
        titles = self._title_candidates(candidates)
        if not titles:
            return None
        query = titles[0]
        normalised = self._normalise_title(query)
        cache = self._read_catalogue_cache()
        cache_key = canonical_hash({"catalogue": "tvmaze", "query": normalised})
        cached = dict((cache.get("entries") or {}).get(cache_key) or {})
        if cached and time.time() - float(cached.get("cached_at_epoch") or 0) < 86_400:
            result = dict(cached.get("result") or {})
            result["catalogue_cache_hit"] = True
            return result

        result: Dict[str, Any] = {
            "programme_query": query,
            "metadata_status": "public_catalogue_unavailable",
            "metadata_confidence": 0.35,
            "catalogue_provider": "TVmaze",
            "catalogue_identity_verified": False,
            "current_playback_verified": False,
            "availability_verified": False,
            "account_entitlement_verified": False,
            "provider_api_called": True,
            "sources": ["https://www.tvmaze.com/api"],
            "attribution": "Programme catalogue data: TVmaze (CC BY-SA)",
            "catalogue_candidates": [],
        }
        try:
            url = "https://api.tvmaze.com/search/shows?" + urllib.parse.urlencode({"q": query})
            payload = self._fetch_json(url)
            rows = list(payload or [])[:10] if isinstance(payload, list) else []
            exact: list[Dict[str, Any]] = []
            visible: list[Dict[str, Any]] = []
            for row in rows:
                show = dict(row.get("show") or {}) if isinstance(row, dict) else {}
                name = " ".join(str(show.get("name") or "").split()).strip()[:160]
                show_id = show.get("id")
                if not name or show_id is None:
                    continue
                item = {
                    "catalogue_id": str(show_id)[:40],
                    "title": name,
                    "premiered": str(show.get("premiered") or "")[:20] or None,
                    "ended": str(show.get("ended") or "")[:20] or None,
                    "type": str(show.get("type") or "")[:60] or None,
                    "language": str(show.get("language") or "")[:60] or None,
                    "official_url": str(show.get("url") or "")[:500] or None,
                }
                visible.append(item)
                if self._normalise_title(name) == normalised:
                    exact.append(item)
            unique_exact = {item["catalogue_id"]: item for item in exact}
            result["catalogue_candidates"] = visible[:5]
            if len(unique_exact) == 1:
                match = next(iter(unique_exact.values()))
                result.update({
                    "provider": "programme_catalogue",
                    "content_id": match["catalogue_id"],
                    "title": match["title"],
                    "official_url": match["official_url"],
                    "premiered": match["premiered"],
                    "ended": match["ended"],
                    "programme_type": match["type"],
                    "language": match["language"],
                    "metadata_status": "public_catalogue_exact_match",
                    "metadata_confidence": 0.9,
                    "catalogue_identity_verified": True,
                })
            elif len(unique_exact) > 1:
                result.update({"metadata_status": "public_catalogue_ambiguous", "metadata_confidence": 0.55})
            else:
                result.update({"metadata_status": "public_catalogue_no_exact_match", "metadata_confidence": 0.4})
        except Exception as exc:
            result["catalogue_error"] = type(exc).__name__

        entries = dict(cache.get("entries") or {})
        entries[cache_key] = {"cached_at_epoch": time.time(), "result": result}
        if len(entries) > 100:
            entries = dict(sorted(
                entries.items(),
                key=lambda item: float((item[1] or {}).get("cached_at_epoch") or 0),
                reverse=True,
            )[:100])
        self._write_catalogue_cache({"schema_version": "pilot.programme-catalogue-cache.v1", "entries": entries})
        return result

    @staticmethod
    def _references(values: Iterable[Any]) -> list[str]:
        references = []
        for value in values:
            text = str(value or "").strip()
            if text.startswith("https://"):
                references.append(text[:1200])
        return references[:10]

    def resolve(
        self,
        references: Iterable[Any],
        *,
        app_id: str = "",
        app_title: str = "",
        programme_candidates: Iterable[Any] = (),
    ) -> Dict[str, Any]:
        refs = self._references(references)
        joined = " ".join(refs)
        record: Dict[str, Any] = {
            "schema_version": "pilot.provider-metadata.v1",
            "created_at": utc_now_iso(),
            "provider": "unknown",
            "content_id": None,
            "title": None,
            "official_url": refs[0] if refs else None,
            "metadata_status": "reference_missing" if not refs else "unrecognized_reference",
            "metadata_confidence": 0.2 if not refs else 0.4,
            "availability_verified": False,
            "account_entitlement_verified": False,
            "provider_api_called": False,
            "sources": [],
            "limitations": ["Playback availability and account entitlement are not inferred from metadata."],
            "app": {"id": app_id[:160], "title": app_title[:160]},
        }
        youtube = self.YOUTUBE_ID.search(joined)
        netflix = self.NETFLIX_ID.search(joined)
        twitch = self.TWITCH_CLIP.search(joined)
        if youtube:
            video_id = youtube.group(1)
            record.update({
                "provider": "youtube",
                "content_id": video_id,
                "official_url": f"https://www.youtube.com/watch?v={video_id}",
                "metadata_status": "provider_identifier_only",
                "metadata_confidence": 0.82,
                "sources": ["https://developers.google.com/youtube/v3/docs/videos/list"],
            })
            api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
            if api_key:
                try:
                    url = "https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode({
                        "part": "snippet,contentDetails,status,liveStreamingDetails",
                        "id": video_id,
                        "key": api_key,
                        "fields": "items(id,snippet(title,channelTitle,publishedAt,liveBroadcastContent),contentDetails(duration,caption),status(embeddable,privacyStatus),liveStreamingDetails(actualStartTime,scheduledStartTime))",
                    })
                    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Pilot-Fabric/0.47.0"})
                    with urllib.request.urlopen(request, timeout=12) as response:
                        payload = response.read(500_001)
                    if len(payload) > 500_000:
                        raise RuntimeError("YouTube metadata exceeded its safety limit")
                    data = json.loads(payload)
                    item = dict((data.get("items") or [{}])[0]) if data.get("items") else {}
                    snippet = dict(item.get("snippet") or {})
                    details = dict(item.get("contentDetails") or {})
                    status = dict(item.get("status") or {})
                    record.update({
                        "title": str(snippet.get("title") or "")[:240] or None,
                        "channel": str(snippet.get("channelTitle") or "")[:160] or None,
                        "published_at": snippet.get("publishedAt"),
                        "duration": details.get("duration"),
                        "captions_available": details.get("caption") == "true",
                        "live_broadcast_content": snippet.get("liveBroadcastContent"),
                        "embeddable": status.get("embeddable"),
                        "metadata_status": "official_api_verified" if item else "official_api_no_match",
                        "metadata_confidence": 0.99 if item else 0.82,
                        "provider_api_called": True,
                    })
                except Exception as exc:
                    record.update({
                        "metadata_status": "official_api_unavailable",
                        "provider_api_called": True,
                        "provider_api_error": type(exc).__name__,
                    })
        elif netflix:
            title_id = netflix.group(1)
            record.update({
                "provider": "netflix",
                "content_id": title_id,
                "official_url": f"https://www.netflix.com/title/{title_id}",
                "metadata_status": "provider_identifier_only",
                "metadata_confidence": 0.84,
                "native_share": "netflix_mobile_moments",
                "sources": ["https://help.netflix.com/en/node/210664027435620"],
                "limitations": [
                    "Netflix title availability depends on the signed-in account and region.",
                    "Netflix Moments is performed in supported Netflix mobile apps; Fabric does not copy programme media.",
                ],
            })
        elif twitch:
            clip_id = twitch.group(1)
            record.update({
                "provider": "twitch",
                "content_id": clip_id,
                "official_url": f"https://clips.twitch.tv/{clip_id}",
                "metadata_status": "provider_identifier_only",
                "metadata_confidence": 0.86,
                "native_share": "twitch_clip",
                "sources": ["https://dev.twitch.tv/docs/embed/video-and-clips/"],
                "limitations": ["Twitch API enrichment requires an explicitly connected developer application."],
            })
        elif "youtube" in f"{app_id} {app_title}".lower():
            record.update({"provider": "youtube", "metadata_status": "content_reference_missing", "metadata_confidence": 0.55})
        elif "netflix" in f"{app_id} {app_title}".lower():
            record.update({"provider": "netflix", "metadata_status": "content_reference_missing", "metadata_confidence": 0.55})
        elif "twitch" in f"{app_id} {app_title}".lower():
            record.update({"provider": "twitch", "metadata_status": "content_reference_missing", "metadata_confidence": 0.55})
        if not record.get("title") and programme_candidates:
            catalogue = self._public_catalogue(programme_candidates)
            if catalogue:
                provider_hint = record.get("provider")
                record.update(catalogue)
                record["application_provider_hint"] = provider_hint if provider_hint != "unknown" else None
                record["limitations"] = [
                    "A public catalogue match identifies a programme record; it does not prove what is currently playing.",
                    "Playback, regional availability and account entitlement require separate signed provider evidence.",
                ]
        record["evidence_hash"] = canonical_hash(record)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(record))
        os.replace(temporary, self.path)
        return record

    def latest(self) -> Dict[str, Any] | None:
        if not self.path.exists():
            return None
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None
