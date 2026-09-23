from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from .canonical import canonical_bytes, utc_now_iso


INTELLIGENCE_MODES = {"native", "gemini", "boost"}


class PilotIntelligencePolicy:
    """Mother-local provider policy. Secrets never enter this record."""

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "intelligence"
        self.path = self.root / "settings.json"
        self.usage_path = self.root / "provider_usage.json"
        self.root.mkdir(parents=True, exist_ok=True)

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def mode(self) -> str:
        env = os.getenv("PILOT_INTELLIGENCE_MODE", "").strip().lower()
        stored = str(self._read().get("mode") or "native").strip().lower()
        return env if env in INTELLIGENCE_MODES else stored if stored in INTELLIGENCE_MODES else "native"

    def gemini_grounding_enabled(self) -> bool:
        env = os.getenv("PILOT_GEMINI_GROUNDING", "").strip().lower()
        if env:
            return env in {"1", "true", "yes", "on"}
        return bool(self._read().get("gemini_grounding_enabled", False))

    def set_mode(self, mode: str, *, gemini_grounding_enabled: bool | None = None) -> Dict[str, Any]:
        normalized = str(mode or "").strip().lower()
        if normalized not in INTELLIGENCE_MODES:
            raise ValueError("Pilot intelligence mode must be native, gemini, or boost")
        current = self._read()
        current.update({"schema_version": "pilot.intelligence.policy.v1", "mode": normalized, "updated_at": utc_now_iso()})
        if gemini_grounding_enabled is not None:
            current["gemini_grounding_enabled"] = bool(gemini_grounding_enabled)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(current))
        os.replace(temporary, self.path)
        return self.status()

    @staticmethod
    def _provider_connected(provider: str) -> bool:
        try:
            from backend.modules.vault.ai_provider_key_store import get_ai_provider_secret

            return bool(str(get_ai_provider_secret(provider) or "").strip())
        except Exception:
            return False

    def status(self) -> Dict[str, Any]:
        mode = self.mode()
        labels = {
            "native": "AION Native",
            "gemini": "AION + Gemini",
            "boost": "Pilot Boost",
        }
        routes = {
            "native": ["deterministic_local", "aion_memory", "local_model", "public_evidence", "honest_limitation"],
            "gemini": ["deterministic_local", "aion_memory", "local_model", "public_evidence", "gemini_synthesis", "optional_gemini_grounding", "honest_limitation"],
            "boost": ["deterministic_local", "aion_memory", "local_model", "public_evidence", "gemini_synthesis", "optional_gemini_grounding", "premium_provider", "honest_limitation"],
        }
        return {
            "schema_version": "pilot.intelligence.policy.v1",
            "mode": mode,
            "label": labels[mode],
            "route": routes[mode],
            "gemini_connected": self._provider_connected("gemini"),
            "openai_connected": self._provider_connected("openai"),
            "gemini_grounding_enabled": self.gemini_grounding_enabled(),
            "secrets_projected_to_tv": False,
            "settings_path": str(self.path),
            "usage": self.usage(),
        }

    def _read_usage(self) -> Dict[str, Any]:
        if not self.usage_path.exists():
            return {"schema_version": "pilot.provider-usage.v1", "days": {}}
        try:
            value = json.loads(self.usage_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {"schema_version": "pilot.provider-usage.v1", "days": {}}
        except (OSError, json.JSONDecodeError):
            return {"schema_version": "pilot.provider-usage.v1", "days": {}}

    def usage(self) -> Dict[str, Any]:
        today = datetime.now(timezone.utc).date().isoformat()
        record = dict((self._read_usage().get("days") or {}).get(today) or {})
        return {"date_utc": today, "providers": record}

    def allowance(self, provider: str) -> bool:
        if provider != "gemini":
            return True
        limit = max(1, int(os.getenv("PILOT_GEMINI_DAILY_SAFETY_LIMIT", "50")))
        used = int(((self.usage().get("providers") or {}).get(provider) or {}).get("requests", 0))
        return used < limit

    def record_provider_call(self, provider: str, *, outcome: str) -> None:
        today = datetime.now(timezone.utc).date().isoformat()
        state = self._read_usage()
        days = state.setdefault("days", {})
        day = days.setdefault(today, {})
        record = day.setdefault(provider, {"requests": 0, "successes": 0, "failures": 0})
        record["requests"] = int(record.get("requests", 0)) + 1
        record["successes" if outcome == "success" else "failures"] = int(record.get("successes" if outcome == "success" else "failures", 0)) + 1
        record["last_outcome"] = outcome
        record["updated_at"] = utc_now_iso()
        temporary = self.usage_path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.replace(temporary, self.usage_path)


def intelligence_label(provider: str, *, has_public_evidence: bool) -> tuple[str, str]:
    if provider.startswith("openai") or provider.startswith("premium"):
        return "pilot_boost", "Pilot Boost"
    if provider.startswith("gemini") or has_public_evidence:
        return "aion_live_evidence", "AION + live public evidence"
    return "aion_local", "AION Local"
