from __future__ import annotations

import json
import os
import re
import threading
import urllib.parse
from pathlib import Path
from typing import Any, Dict

from .canonical import canonical_bytes, utc_now_iso
from .research import AionTVResearch


class EntertainmentIntelligence:
    """Evidence-labelled cross-service discovery and household watch memory."""

    _lock = threading.RLock()
    _provider_hosts = {
        "netflix.com": "Netflix",
        "primevideo.com": "Prime Video",
        "amazon.com": "Prime Video",
        "disneyplus.com": "Disney+",
        "youtube.com": "YouTube",
        "justwatch.com": "JustWatch",
    }

    def __init__(self, runtime_dir: str | Path, *, researcher: AionTVResearch | None = None) -> None:
        root = Path(runtime_dir) / "entertainment"
        root.mkdir(parents=True, exist_ok=True)
        self.state_path = root / "state.json"
        self.latest_path = root / "latest.json"
        self.researcher = researcher or AionTVResearch(runtime_dir)

    @staticmethod
    def _initial() -> Dict[str, Any]:
        return {
            "schema_version": "aion.entertainment.memory.v1",
            "region": "ES",
            "preferred_services": ["Netflix", "Prime Video", "Disney+", "YouTube"],
            "audio_language": "original",
            "subtitle_language": "English",
            "subtitles_preferred": False,
            "history": [],
            "updated_at": utc_now_iso(),
        }

    def _load(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            return self._initial()
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else self._initial()
        except (OSError, json.JSONDecodeError):
            return self._initial()

    def _save(self, state: Dict[str, Any]) -> None:
        state["updated_at"] = utc_now_iso()
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.replace(temporary, self.state_path)

    @classmethod
    def _provider(cls, url: str) -> str:
        host = re.sub(r"^www\.", "", urllib.parse.urlparse(url).hostname or "")
        return next((name for suffix, name in cls._provider_hosts.items() if host == suffix or host.endswith(f".{suffix}")), "Web evidence")

    def discover(self, request: str, *, people: str | None = None, minutes: int | None = None) -> Dict[str, Any]:
        request = " ".join(request.split()).strip()[:300]
        if len(request) < 2:
            raise ValueError("The entertainment request is too short")
        state = self._load()
        history = [item for item in state.get("history", []) if item.get("household_shared") is True and item.get("outcome") in {"watched", "disliked", "avoid"}]
        context = [f"Spain region ({state.get('region', 'ES')})", "check Netflix, Prime Video, Disney+ and YouTube"]
        if people:
            context.append(f"watching with {people[:80]}")
        if minutes:
            context.append(f"maximum runtime about {max(10, min(int(minutes), 360))} minutes")
        if history:
            context.append("avoid already watched or rejected: " + ", ".join(str(item.get("title")) for item in history[-12:]))
        query = f"{request}. " + ". ".join(context)
        research = self.researcher.search(query, mode="streaming")
        items = []
        for item in list(research.get("items") or [])[:5]:
            provider = self._provider(str(item.get("url") or ""))
            items.append({
                **item,
                "provider": provider,
                "availability": "provider_or_catalogue_page_found" if provider != "Web evidence" else "requires_current_provider_confirmation",
                "availability_region": str(state.get("region") or "ES"),
            })
        record = {
            "schema_version": "aion.entertainment.discovery.v1",
            "request": request,
            "answer": research.get("answer"),
            "items": items,
            "criteria": {"people": people, "minutes": minutes, "region": state.get("region", "ES")},
            "services_checked": list(state.get("preferred_services") or []),
            "evidence_provider": research.get("provider"),
            "availability_policy": "Never claim subscription availability without current evidence; confirm inside the signed-in provider before playback.",
            "created_at": utc_now_iso(),
        }
        temporary = self.latest_path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(record))
        os.replace(temporary, self.latest_path)
        return record

    def remember(self, title: str, outcome: str) -> Dict[str, Any]:
        title = " ".join(title.split()).strip()[:160]
        if len(title) < 1 or outcome not in {"watched", "liked", "disliked", "avoid"}:
            raise ValueError("Invalid entertainment memory")
        with self._lock:
            state = self._load()
            history = [item for item in state.get("history", []) if str(item.get("title", "")).lower() != title.lower()][-99:]
            history.append({"title": title, "outcome": outcome, "recorded_at": utc_now_iso()})
            state["history"] = history
            self._save(state)
            return dict(history[-1])

    def latest(self) -> Dict[str, Any] | None:
        try:
            value = json.loads(self.latest_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def snapshot(self) -> Dict[str, Any]:
        state = self._load()
        return {
            "region": state.get("region"),
            "preferred_services": list(state.get("preferred_services") or []),
            "audio_language": state.get("audio_language"),
            "subtitle_language": state.get("subtitle_language"),
            "subtitles_preferred": bool(state.get("subtitles_preferred")),
            "history_count": len(state.get("history") or []),
            "latest": self.latest(),
            "updated_at": state.get("updated_at"),
        }
