# /workspaces/COMDEX/backend/modules/aion_equities/company_trigger_map_store.py
from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.constants import SCHEMA_PACK_VERSION
from backend.modules.aion_equities.schema_validate import validate_or_false


VALID_TRIGGER_STATES = {
    "inactive",
    "early_watch",
    "building",
    "confirmed",
    "broken",
}

VALID_IMPACT_DIRECTIONS = {
    "positive",
    "negative",
    "mixed",
    "unknown",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_z(value: Any) -> str:
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, str):
        return value
    raise ValueError(f"Unsupported datetime value: {value!r}")


def _date_str(value: Any) -> str:
    if isinstance(value, datetime):
        return _iso_z(value)[:10]
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        s = value.strip()
        if len(s) >= 10:
            return s[:10]
    raise ValueError(f"Unsupported date value: {value!r}")


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
    return Path(__file__).resolve().parent / "data" / "company_trigger_maps"


def company_trigger_map_storage_path(
    company_ref: str,
    fiscal_period_ref: str,
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    return root / _safe_segment(company_ref) / f"{_safe_segment(fiscal_period_ref)}.json"


def _normalize_trigger_state(value: Any) -> str:
    s = str(value or "inactive").strip().lower()
    return s if s in VALID_TRIGGER_STATES else "inactive"


def _normalize_impact_direction(value: Any) -> str:
    s = str(value or "unknown").strip().lower()
    return s if s in VALID_IMPACT_DIRECTIONS else "unknown"


def _normalize_confidence(value: Any) -> float:
    try:
        x = float(value)
    except Exception:
        x = 0.0
    return max(0.0, min(100.0, x))


def _normalize_impact_weight(value: Any) -> float:
    try:
        x = float(value)
    except Exception:
        x = 0.0
    return max(0.0, min(1.0, x))


def _as_str(x: Any) -> str:
    return str(x).strip() if x is not None else ""


def _normalize_feed_id(item: Dict[str, Any]) -> Optional[str]:
    """
    Preferred: item["feed_id"].

    Also tolerate:
      - source_feed_id
      - data_source_id
      - feed_key
      - feed
    """
    for k in ("feed_id", "source_feed_id", "data_source_id", "feed_key", "feed"):
        v = _as_str(item.get(k))
        if v:
            return v
    return None


def _trigger_matches_feed_id(trigger: Dict[str, Any], feed_id: str) -> bool:
    """
    IMPORTANT:
    - feed_id is the machine key used by FeedRegistry / LiveVariableTracker.
    - data_source is often a human label, so do NOT rely on it.
    - But keep data_source == feed_id as a last-resort legacy fallback.
    """
    fid = _as_str(feed_id)
    if not fid:
        return False

    t_fid = _as_str(trigger.get("feed_id"))
    if t_fid == fid and t_fid:
        return True

    # tolerate old keys
    for k in ("source_feed_id", "data_source_id", "feed_key", "feed"):
        if _as_str(trigger.get(k)) == fid:
            return True

    # last resort legacy (dangerous but preserves older maps)
    if _as_str(trigger.get("data_source")) == fid:
        return True

    return False


def _normalize_trigger_item(
    item: Any,
    *,
    company_ref: str,
    fiscal_period_ref: str,
) -> Dict[str, Any]:
    """
    Accepts:
      - dict (preferred)
      - str (treated as a variable name / trigger label)
      - any other type (stringified)
    Produces a canonical trigger entry dict.

    Canonical fields include BOTH:
      - data_source (human readable label)
      - feed_id (machine feed key used by LiveVariableTracker)
    """
    # --- coerce non-dict forms into a dict ---
    if isinstance(item, str):
        item = {"variable_name": item}
    elif not isinstance(item, dict):
        item = {"variable_name": str(item)}

    trigger_id = _as_str(item.get("trigger_id"))
    variable_name = _as_str(item.get("variable_name") or item.get("name") or item.get("type"))

    # HUMAN label only (do not fall back to feed_id here)
    data_source = _as_str(item.get("data_source") or item.get("source"))

    # MACHINE key (feed_id)
    feed_id = _normalize_feed_id(item)

    # allow "details" -> notes for the OpenAI style triggers you showed
    notes = item.get("notes")
    if notes is None and item.get("details") is not None:
        notes = item.get("details")

    if not trigger_id:
        slug = _safe_segment(variable_name or feed_id or data_source or "trigger").lower()
        trigger_id = f"{company_ref}/trigger/{fiscal_period_ref}/{slug}"

    out: Dict[str, Any] = {
        "trigger_id": trigger_id,
        "variable_name": variable_name or "unknown_variable",
        "data_source": data_source or "unknown_source",
        "current_state": _normalize_trigger_state(item.get("current_state")),
        "threshold_rule": _as_str(item.get("threshold_rule")),
        "lag_expectation": _as_str(item.get("lag_expectation")),
        "impact_direction": _normalize_impact_direction(item.get("impact_direction")),
        "impact_weight": _normalize_impact_weight(item.get("impact_weight")),
        "confidence": _normalize_confidence(item.get("confidence")),
        "thesis_action": _as_str(item.get("thesis_action")),
    }

    # NEW: persist feed_id if available
    if feed_id:
        out["feed_id"] = feed_id

    if notes is not None:
        out["notes"] = deepcopy(notes)

    # Pass-through fields that runtime may mutate
    optional_fields = [
        "linked_report_ref",
        "last_observed_value",
        "next_check_date",
        "latest_value",
        "last_updated_at",
        "update_history",
        # tolerate legacy feed keys too (kept if present)
        "source_feed_id",
        "data_source_id",
        "feed_key",
        "feed",
    ]
    for field in optional_fields:
        if field in item and item[field] is not None and field not in out:
            out[field] = deepcopy(item[field])

    return out


def _normalize_trigger_entries(
    entries: Optional[List[Any]],
    *,
    company_ref: str,
    fiscal_period_ref: str,
) -> List[Dict[str, Any]]:
    if not entries:
        return []
    return [
        _normalize_trigger_item(
            deepcopy(item),
            company_ref=company_ref,
            fiscal_period_ref=fiscal_period_ref,
        )
        for item in entries
    ]


def _with_legacy_aliases(payload: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(payload)

    if "trigger_entries" in out and "triggers" not in out:
        out["triggers"] = deepcopy(out["trigger_entries"])
    elif "triggers" in out and "trigger_entries" not in out:
        out["trigger_entries"] = deepcopy(out["triggers"])

    return out


def _strip_legacy_aliases(payload: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(payload)

    # Canonicalise onto trigger_entries before writing.
    # Prefer the live "triggers" view if present, because runtime code mutates that.
    if "triggers" in out:
        out["trigger_entries"] = deepcopy(out["triggers"])
    elif "trigger_entries" not in out:
        out["trigger_entries"] = []

    out.pop("triggers", None)
    return out


def build_company_trigger_map_payload(
    *,
    company_ref: str,
    fiscal_period_ref: str,
    generated_by: str = "aion_equities.company_trigger_map_store",
    trigger_entries: Optional[List[Dict[str, Any]]] = None,
    summary_patch: Optional[Dict[str, Any]] = None,
    linked_refs_patch: Optional[Dict[str, Any]] = None,
    payload_patch: Optional[Dict[str, Any]] = None,
    created_at: Optional[Any] = None,
    updated_at: Optional[Any] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    created_at_s = _iso_z(created_at) if created_at is not None else _utc_now_iso()
    updated_at_s = _iso_z(updated_at) if updated_at is not None else created_at_s

    payload: Dict[str, Any] = {
        "company_trigger_map_id": f"{company_ref}/trigger_map/{fiscal_period_ref}",
        "company_ref": company_ref,
        "fiscal_period_ref": fiscal_period_ref,
        "trigger_entries": _normalize_trigger_entries(
            trigger_entries,
            company_ref=company_ref,
            fiscal_period_ref=fiscal_period_ref,
        ),
        "summary": {
            "active_trigger_count": 0,
            "confirmed_trigger_count": 0,
            "broken_trigger_count": 0,
            "notes": "",
        },
        "audit": {
            "created_at": created_at_s,
            "updated_at": updated_at_s,
            "created_by": generated_by,
        },
    }

    if summary_patch:
        payload["summary"] = _deep_merge(payload["summary"], deepcopy(summary_patch))
    if linked_refs_patch:
        payload["linked_refs"] = deepcopy(linked_refs_patch)
    if payload_patch:
        payload = _deep_merge(payload, deepcopy(payload_patch))

    if "triggers" in payload and "trigger_entries" not in payload:
        payload["trigger_entries"] = deepcopy(payload["triggers"])

    payload["trigger_entries"] = _normalize_trigger_entries(
        payload.get("trigger_entries"),
        company_ref=company_ref,
        fiscal_period_ref=fiscal_period_ref,
    )

    active_count = 0
    confirmed_count = 0
    broken_count = 0
    for entry in payload["trigger_entries"]:
        state = entry.get("current_state", "inactive")
        if state != "inactive":
            active_count += 1
        if state == "confirmed":
            confirmed_count += 1
        if state == "broken":
            broken_count += 1

    payload["summary"]["active_trigger_count"] = active_count
    payload["summary"]["confirmed_trigger_count"] = confirmed_count
    payload["summary"]["broken_trigger_count"] = broken_count

    payload = _with_legacy_aliases(payload)

    if validate:
        validate_or_false(
            "company_trigger_map",
            _strip_legacy_aliases(payload),
            version=SCHEMA_PACK_VERSION,
        )

    return payload


def save_company_trigger_map_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Path:
    canonical_payload = _strip_legacy_aliases(payload)

    canonical_payload["trigger_entries"] = _normalize_trigger_entries(
        canonical_payload.get("trigger_entries"),
        company_ref=canonical_payload["company_ref"],
        fiscal_period_ref=canonical_payload["fiscal_period_ref"],
    )

    if validate:
        validate_or_false("company_trigger_map", canonical_payload, version=SCHEMA_PACK_VERSION)

    path = company_trigger_map_storage_path(
        canonical_payload["company_ref"],
        canonical_payload["fiscal_period_ref"],
        base_dir=base_dir,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(canonical_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_company_trigger_map_payload(
    company_ref: str,
    fiscal_period_ref: str,
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    path = company_trigger_map_storage_path(
        company_ref,
        fiscal_period_ref,
        base_dir=base_dir,
    )
    if not path.exists():
        raise FileNotFoundError(f"Company trigger map not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if validate:
        validate_or_false("company_trigger_map", payload, version=SCHEMA_PACK_VERSION)
    return _with_legacy_aliases(payload)


class CompanyTriggerMapStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "company_trigger_maps"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, company_ref: str, fiscal_period_ref: str) -> Path:
        return company_trigger_map_storage_path(
            company_ref,
            fiscal_period_ref,
            base_dir=self.base_dir,
        )

    def save_company_trigger_map(
        self,
        *,
        company_ref: str,
        fiscal_period_ref: str,
        generated_by: str = "aion_equities.company_trigger_map_store",
        trigger_entries: Optional[List[Dict[str, Any]]] = None,
        summary_patch: Optional[Dict[str, Any]] = None,
        linked_refs_patch: Optional[Dict[str, Any]] = None,
        payload_patch: Optional[Dict[str, Any]] = None,
        validate: bool = True,
        **legacy_kwargs: Any,
    ) -> Dict[str, Any]:
        if trigger_entries is None:
            trigger_entries = legacy_kwargs.pop("triggers", None)

        created_at = legacy_kwargs.pop("created_at", None)
        updated_at = legacy_kwargs.pop("updated_at", None)
        legacy_kwargs.pop("as_of_date", None)

        payload = build_company_trigger_map_payload(
            company_ref=company_ref,
            fiscal_period_ref=fiscal_period_ref,
            generated_by=generated_by,
            trigger_entries=trigger_entries,
            summary_patch=summary_patch,
            linked_refs_patch=linked_refs_patch,
            payload_patch=payload_patch,
            created_at=created_at,
            updated_at=updated_at,
            validate=validate,
        )
        save_company_trigger_map_payload(
            payload,
            base_dir=self.base_dir,
            validate=False,
        )
        return payload

    def save_trigger_map(self, **kwargs: Any) -> Dict[str, Any]:
        return self.save_company_trigger_map(**kwargs)

    def save_trigger_map_payload(
        self,
        payload: Dict[str, Any],
        *,
        validate: bool = True,
    ) -> Path:
        return save_company_trigger_map_payload(
            payload,
            base_dir=self.base_dir,
            validate=validate,
        )

    def load_company_trigger_map(
        self,
        company_ref: str,
        fiscal_period_ref: str,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return load_company_trigger_map_payload(
            company_ref,
            fiscal_period_ref,
            base_dir=self.base_dir,
            validate=validate,
        )

    def load_trigger_map(
        self,
        company_ref: str,
        fiscal_period_ref: str,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return self.load_company_trigger_map(
            company_ref,
            fiscal_period_ref,
            validate=validate,
        )

    def load_company_trigger_map_by_id(
        self,
        company_trigger_map_id: str,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        parts = str(company_trigger_map_id).split("/trigger_map/")
        if len(parts) != 2:
            raise ValueError(f"Invalid company_trigger_map_id: {company_trigger_map_id!r}")
        company_ref, fiscal_period_ref = parts
        return self.load_company_trigger_map(
            company_ref,
            fiscal_period_ref,
            validate=validate,
        )

    def load_trigger_map_by_id(
        self,
        company_trigger_map_id: str,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return self.load_company_trigger_map_by_id(
            company_trigger_map_id,
            validate=validate,
        )

    def load_latest_trigger_map(
        self,
        company_ref: str,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        fiscal_periods = self.list_trigger_maps(company_ref)
        if not fiscal_periods:
            raise FileNotFoundError(f"No trigger maps found for company_ref={company_ref}")
        latest_period = sorted(fiscal_periods)[-1]
        return self.load_company_trigger_map(
            company_ref,
            latest_period,
            validate=validate,
        )

    def trigger_map_exists(self, company_ref: str, fiscal_period_ref: str) -> bool:
        return self.storage_path(company_ref, fiscal_period_ref).exists()

    def company_trigger_map_exists(self, company_ref: str, fiscal_period_ref: str) -> bool:
        return self.trigger_map_exists(company_ref, fiscal_period_ref)

    def list_trigger_maps(self, company_ref: str) -> List[str]:
        company_dir = self.base_dir / _safe_segment(company_ref)
        if not company_dir.exists():
            return []
        return sorted(p.stem for p in company_dir.glob("*.json"))

    def list_trigger_maps_by_feed(
        self,
        feed_id: str,
        *,
        validate: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Returns trigger maps that contain at least one trigger matching feed_id.

        Matching uses:
          - trigger.feed_id (preferred)
          - trigger.source_feed_id / trigger.data_source_id / trigger.feed_key / trigger.feed
          - trigger.data_source == feed_id (legacy fallback)
        """
        fid = _as_str(feed_id)
        out: List[Dict[str, Any]] = []
        if not fid:
            return out

        if not self.base_dir.exists():
            return out

        for company_dir in sorted(p for p in self.base_dir.iterdir() if p.is_dir()):
            for json_file in sorted(company_dir.glob("*.json")):
                try:
                    payload = json.loads(json_file.read_text(encoding="utf-8"))
                    if validate:
                        validate_or_false("company_trigger_map", payload, version=SCHEMA_PACK_VERSION)

                    payload = _with_legacy_aliases(payload)
                    triggers = payload.get("triggers", []) or []

                    if any(isinstance(t, dict) and _trigger_matches_feed_id(t, fid) for t in triggers):
                        out.append(payload)
                except Exception:
                    continue

        return out


__all__ = [
    "build_company_trigger_map_payload",
    "save_company_trigger_map_payload",
    "load_company_trigger_map_payload",
    "CompanyTriggerMapStore",
]