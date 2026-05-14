from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.constants import SCHEMA_PACK_VERSION
from backend.modules.aion_equities.schema_validate import validate_payload


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
    return Path(__file__).resolve().parent / "data" / "credit_trajectory"


def credit_trajectory_storage_path(
    entity_ref: str,
    as_of_date: Any,
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    return root / _safe_segment(entity_ref) / f"{_safe_segment(_date_str(as_of_date))}.json"


def _normalize_official_rating_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch
    return deepcopy(patch)


def _normalize_shadow_rating_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch
    return deepcopy(patch)


def _normalize_trajectory_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch

    src = deepcopy(patch)
    out: Dict[str, Any] = {}

    # canonical keys
    for key in ("state", "downgrade_risk", "upgrade_potential", "watch_window_days", "notes"):
        if key in src:
            out[key] = src[key]

    # legacy runtime keys are intentionally NOT left in trajectory
    # because the locked schema rejects them.
    legacy_notes: List[str] = []
    if "direction" in src:
        legacy_notes.append(f"direction={src['direction']}")
    if "momentum" in src:
        legacy_notes.append(f"momentum={src['momentum']}")
    if "confidence" in src:
        legacy_notes.append(f"confidence={src['confidence']}")

    if legacy_notes:
        existing_notes = str(out.get("notes", "")).strip()
        joined = "; ".join(legacy_notes)
        out["notes"] = f"{existing_notes}; {joined}".strip("; ").strip()

    return out


def _normalize_signals_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch
    return deepcopy(patch)


def _normalize_linked_refs_patch(patch: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patch:
        return patch
    return deepcopy(patch)


def _map_rating_patch_to_canonical(patch: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Backward-compat bridge for runtime tests using rating_state_patch.
    """
    if not patch:
        return {
            "official_rating_patch": {},
            "shadow_rating_patch": {},
            "trajectory_patch": {},
        }

    src = deepcopy(patch)

    official: Dict[str, Any] = {}
    shadow: Dict[str, Any] = {}
    trajectory: Dict[str, Any] = {}

    current_rating = src.get("current_rating", src.get("composite"))
    if current_rating is not None:
        official["composite"] = current_rating

    if "outlook" in src:
        official["outlook"] = src["outlook"]

    if "sp" in src:
        official["sp"] = src["sp"]
    if "moodys" in src:
        official["moodys"] = src["moodys"]
    if "fitch" in src:
        official["fitch"] = src["fitch"]

    rating_agency_mix = src.get("rating_agency_mix")
    if isinstance(rating_agency_mix, list):
        shadow["notes"] = f"rating_agency_mix={','.join(str(x) for x in rating_agency_mix)}"

    if "shadow_composite" in src:
        shadow["composite"] = src["shadow_composite"]
    if "shadow_confidence" in src:
        shadow["confidence"] = src["shadow_confidence"]
    if "shadow_direction" in src:
        shadow["direction"] = src["shadow_direction"]
    if "shadow_notes" in src:
        existing = str(shadow.get("notes", "")).strip()
        extra = str(src["shadow_notes"]).strip()
        shadow["notes"] = f"{existing}; {extra}".strip("; ").strip()

    if "state" in src:
        trajectory["state"] = src["state"]
    if "downgrade_risk" in src:
        trajectory["downgrade_risk"] = src["downgrade_risk"]
    if "upgrade_potential" in src:
        trajectory["upgrade_potential"] = src["upgrade_potential"]
    if "watch_window_days" in src:
        trajectory["watch_window_days"] = src["watch_window_days"]
    if "notes" in src:
        trajectory["notes"] = src["notes"]

    return {
        "official_rating_patch": official,
        "shadow_rating_patch": shadow,
        "trajectory_patch": trajectory,
    }


def _map_outlook_patch_to_canonical(patch: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    if not patch:
        return {"official_rating_patch": {}, "trajectory_patch": {}}

    src = deepcopy(patch)
    official: Dict[str, Any] = {}
    trajectory: Dict[str, Any] = {}

    if "outlook" in src:
        official["outlook"] = src["outlook"]
    if "watch_window_days" in src:
        trajectory["watch_window_days"] = src["watch_window_days"]
    if "state" in src:
        trajectory["state"] = src["state"]
    if "notes" in src:
        trajectory["notes"] = src["notes"]

    return {
        "official_rating_patch": official,
        "trajectory_patch": trajectory,
    }


def _map_pressure_patch_to_canonical(patch: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Backward-compat bridge for runtime tests using catalyst_flags_patch.
    """
    if not patch:
        return {"trajectory_patch": {}, "signals_patch": {}}

    src = deepcopy(patch)
    trajectory: Dict[str, Any] = {}
    signals: Dict[str, Any] = {}

    downgrade_candidate = bool(src.get("downgrade_candidate", False))
    fallen_angel_risk = bool(src.get("fallen_angel_risk", False))
    upgrade_candidate = bool(src.get("upgrade_candidate", False))
    rising_star_potential = bool(src.get("rising_star_potential", False))

    if fallen_angel_risk:
        trajectory["state"] = "fallen_angel_risk"
        trajectory["downgrade_risk"] = 85.0
        trajectory["upgrade_potential"] = 0.0
    elif downgrade_candidate:
        trajectory["state"] = "downgrade_candidate"
        trajectory["downgrade_risk"] = 70.0
        trajectory["upgrade_potential"] = 0.0
    elif rising_star_potential:
        trajectory["state"] = "rising_star_candidate"
        trajectory["upgrade_potential"] = 85.0
        trajectory["downgrade_risk"] = 0.0
    elif upgrade_candidate:
        trajectory["state"] = "upgrade_candidate"
        trajectory["upgrade_potential"] = 70.0
        trajectory["downgrade_risk"] = 0.0

    if "state" in src:
        raw_state = str(src["state"]).strip().lower()
        state_map = {
            "deteriorating": "downgrade_candidate",
            "improving": "upgrade_candidate",
            "stable": "stable",
            "downgrade_candidate": "downgrade_candidate",
            "upgrade_candidate": "upgrade_candidate",
            "fallen_angel_risk": "fallen_angel_risk",
            "rising_star_candidate": "rising_star_candidate",
            "rising_star_potential": "rising_star_candidate",
            "stressed": "stressed",
            "unknown": "unknown",
        }
        trajectory["state"] = state_map.get(raw_state, "unknown")

    if "downgrade_risk" in src:
        trajectory["downgrade_risk"] = src["downgrade_risk"]
    if "upgrade_potential" in src:
        trajectory["upgrade_potential"] = src["upgrade_potential"]
    if "watch_window_days" in src:
        trajectory["watch_window_days"] = src["watch_window_days"]

    notes_parts: List[str] = []
    if downgrade_candidate:
        notes_parts.append("downgrade_candidate=true")
    if fallen_angel_risk:
        notes_parts.append("fallen_angel_risk=true")
    if upgrade_candidate:
        notes_parts.append("upgrade_candidate=true")
    if rising_star_potential:
        notes_parts.append("rising_star_potential=true")
    if "notes" in src:
        notes_parts.append(str(src["notes"]))
    if notes_parts:
        trajectory["notes"] = "; ".join(notes_parts)

    signal_keys = [
        "leverage_signal",
        "coverage_signal",
        "liquidity_signal",
        "spread_signal",
        "refinancing_signal",
    ]
    for key in signal_keys:
        if key in src:
            signals[key] = src[key]

    return {
        "trajectory_patch": trajectory,
        "signals_patch": signals,
    }


def build_credit_trajectory_payload(
    *,
    entity_ref: str,
    entity_type: str,
    as_of_date: Any,
    generated_by: str = "aion_equities.credit_trajectory_store",
    official_rating_patch: Optional[Dict[str, Any]] = None,
    shadow_rating_patch: Optional[Dict[str, Any]] = None,
    trajectory_patch: Optional[Dict[str, Any]] = None,
    signals_patch: Optional[Dict[str, Any]] = None,
    linked_refs_patch: Optional[Dict[str, Any]] = None,
    payload_patch: Optional[Dict[str, Any]] = None,
    created_at: Optional[Any] = None,
    updated_at: Optional[Any] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    as_of_date_s = _date_str(as_of_date)
    created_at_s = _iso_z(created_at) if created_at is not None else _utc_now_iso()
    updated_at_s = _iso_z(updated_at) if updated_at is not None else created_at_s

    official_rating_patch = _normalize_official_rating_patch(official_rating_patch)
    shadow_rating_patch = _normalize_shadow_rating_patch(shadow_rating_patch)
    trajectory_patch = _normalize_trajectory_patch(trajectory_patch)
    signals_patch = _normalize_signals_patch(signals_patch)
    linked_refs_patch = _normalize_linked_refs_patch(linked_refs_patch)

    payload: Dict[str, Any] = {
        "credit_trajectory_id": f"{entity_ref}/credit/{as_of_date_s}",
        "entity_ref": entity_ref,
        "entity_type": entity_type,
        "as_of_date": as_of_date_s,
        "official_rating": {
            "composite": "NR",
            "outlook": "unknown",
        },
        "shadow_rating": {
            "composite": "NR",
            "confidence": 0.0,
            "direction": "unknown",
            "notes": "",
        },
        "trajectory": {
            "state": "unknown",
            "downgrade_risk": 0.0,
            "upgrade_potential": 0.0,
            "watch_window_days": 0,
            "notes": "",
        },
        "signals": {
            "leverage_signal": "unknown",
            "coverage_signal": "unknown",
            "liquidity_signal": "unknown",
            "spread_signal": "unknown",
            "refinancing_signal": "unknown",
        },
        "audit": {
            "created_at": created_at_s,
            "updated_at": updated_at_s,
            "created_by": generated_by,
        },
    }

    if official_rating_patch:
        payload["official_rating"] = _deep_merge(payload["official_rating"], official_rating_patch)
    if shadow_rating_patch:
        payload["shadow_rating"] = _deep_merge(payload["shadow_rating"], shadow_rating_patch)
    if trajectory_patch:
        payload["trajectory"] = _deep_merge(payload["trajectory"], trajectory_patch)
    if signals_patch:
        payload["signals"] = _deep_merge(payload["signals"], signals_patch)
    if linked_refs_patch:
        payload["linked_refs"] = deepcopy(linked_refs_patch)
    if payload_patch:
        payload = _deep_merge(payload, payload_patch)

    # final schema-safe normalization in case payload_patch injected legacy keys
    if isinstance(payload.get("trajectory"), dict):
        payload["trajectory"] = _normalize_trajectory_patch(payload["trajectory"])
    if isinstance(payload.get("official_rating"), dict):
        payload["official_rating"] = _normalize_official_rating_patch(payload["official_rating"])
    if isinstance(payload.get("shadow_rating"), dict):
        payload["shadow_rating"] = _normalize_shadow_rating_patch(payload["shadow_rating"])
    if isinstance(payload.get("signals"), dict):
        payload["signals"] = _normalize_signals_patch(payload["signals"])
    if isinstance(payload.get("linked_refs"), dict):
        payload["linked_refs"] = _normalize_linked_refs_patch(payload["linked_refs"])

    if validate:
        validate_payload("credit_trajectory", payload, version=SCHEMA_PACK_VERSION)

    return payload


def save_credit_trajectory_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Path:
    if validate:
        validate_payload("credit_trajectory", payload, version=SCHEMA_PACK_VERSION)

    path = credit_trajectory_storage_path(
        payload["entity_ref"],
        payload["as_of_date"],
        base_dir=base_dir,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_credit_trajectory_payload(
    entity_ref: str,
    as_of_date: Any,
    *,
    base_dir: Optional[Path] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    path = credit_trajectory_storage_path(entity_ref, as_of_date, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Credit trajectory payload not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if validate:
        validate_payload("credit_trajectory", payload, version=SCHEMA_PACK_VERSION)
    return payload


class CreditTrajectoryStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "credit_trajectory"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, entity_ref: str, as_of_date: Any) -> Path:
        return credit_trajectory_storage_path(entity_ref, as_of_date, base_dir=self.base_dir)

    def load_credit_trajectory_by_id(
        self,
        credit_trajectory_id: str,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        parts = str(credit_trajectory_id).split("/credit/")
        if len(parts) != 2:
            raise ValueError(f"Invalid credit_trajectory_id: {credit_trajectory_id!r}")
        entity_ref, as_of_date = parts
        return self.load_credit_trajectory(
            entity_ref,
            as_of_date,
            validate=validate,
        )

    def load_profile_by_id(
        self,
        credit_trajectory_id: str,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return self.load_credit_trajectory_by_id(
            credit_trajectory_id,
            validate=validate,
        )

    def save_credit_trajectory(
        self,
        *,
        entity_ref: str,
        entity_type: str,
        as_of_date: Any,
        generated_by: str = "aion_equities.credit_trajectory_store",
        official_rating_patch: Optional[Dict[str, Any]] = None,
        shadow_rating_patch: Optional[Dict[str, Any]] = None,
        trajectory_patch: Optional[Dict[str, Any]] = None,
        signals_patch: Optional[Dict[str, Any]] = None,
        rating_patch: Optional[Dict[str, Any]] = None,
        outlook_patch: Optional[Dict[str, Any]] = None,
        pressure_patch: Optional[Dict[str, Any]] = None,
        linked_refs_patch: Optional[Dict[str, Any]] = None,
        payload_patch: Optional[Dict[str, Any]] = None,
        validate: bool = True,
        **legacy_kwargs: Any,
    ) -> Dict[str, Any]:
        if rating_patch is None and "rating_state_patch" in legacy_kwargs:
            rating_patch = legacy_kwargs.pop("rating_state_patch")

        if pressure_patch is None and "catalyst_flags_patch" in legacy_kwargs:
            pressure_patch = legacy_kwargs.pop("catalyst_flags_patch")

        if rating_patch:
            mapped = _map_rating_patch_to_canonical(rating_patch)
            if mapped["official_rating_patch"]:
                official_rating_patch = _deep_merge(
                    official_rating_patch or {},
                    mapped["official_rating_patch"],
                )
            if mapped["shadow_rating_patch"]:
                shadow_rating_patch = _deep_merge(
                    shadow_rating_patch or {},
                    mapped["shadow_rating_patch"],
                )
            if mapped["trajectory_patch"]:
                trajectory_patch = _deep_merge(
                    trajectory_patch or {},
                    mapped["trajectory_patch"],
                )

        if outlook_patch:
            mapped = _map_outlook_patch_to_canonical(outlook_patch)
            if mapped["official_rating_patch"]:
                official_rating_patch = _deep_merge(
                    official_rating_patch or {},
                    mapped["official_rating_patch"],
                )
            if mapped["trajectory_patch"]:
                trajectory_patch = _deep_merge(
                    trajectory_patch or {},
                    mapped["trajectory_patch"],
                )

        if pressure_patch:
            mapped = _map_pressure_patch_to_canonical(pressure_patch)
            if mapped["trajectory_patch"]:
                trajectory_patch = _deep_merge(
                    trajectory_patch or {},
                    mapped["trajectory_patch"],
                )
            if mapped["signals_patch"]:
                signals_patch = _deep_merge(
                    signals_patch or {},
                    mapped["signals_patch"],
                )

        # absorb legacy runtime-only trajectory fields into schema-safe canonical fields
        if trajectory_patch:
            legacy_conf = trajectory_patch.pop("confidence", None) if "confidence" in trajectory_patch else None
            legacy_dir = trajectory_patch.pop("direction", None) if "direction" in trajectory_patch else None
            legacy_momentum = trajectory_patch.pop("momentum", None) if "momentum" in trajectory_patch else None

            if legacy_conf is not None:
                shadow_rating_patch = _deep_merge(
                    shadow_rating_patch or {},
                    {"confidence": legacy_conf},
                )

            if legacy_dir is not None:
                dir_s = str(legacy_dir).strip().lower()
                shadow_rating_patch = _deep_merge(
                    shadow_rating_patch or {},
                    {
                        "direction": (
                            "deteriorating" if dir_s in {"deteriorating", "negative", "down"}
                            else "improving" if dir_s in {"improving", "positive", "up"}
                            else "stable" if dir_s == "stable"
                            else "unknown"
                        )
                    },
                )

                current_state = str(trajectory_patch.get("state", "unknown")).strip().lower()
                if current_state in {"", "unknown"}:
                    if dir_s in {"deteriorating", "negative", "down"}:
                        trajectory_patch["state"] = "downgrade_candidate"
                    elif dir_s in {"improving", "positive", "up"}:
                        trajectory_patch["state"] = "upgrade_candidate"
                    elif dir_s == "stable":
                        trajectory_patch["state"] = "stable"

            if legacy_momentum is not None:
                notes = str(trajectory_patch.get("notes", "")).strip()
                extra = f"momentum={legacy_momentum}"
                trajectory_patch["notes"] = f"{notes}; {extra}".strip("; ").strip()

        payload = build_credit_trajectory_payload(
            entity_ref=entity_ref,
            entity_type=entity_type,
            as_of_date=as_of_date,
            generated_by=generated_by,
            official_rating_patch=official_rating_patch,
            shadow_rating_patch=shadow_rating_patch,
            trajectory_patch=trajectory_patch,
            signals_patch=signals_patch,
            linked_refs_patch=linked_refs_patch,
            payload_patch=payload_patch,
            validate=validate,
        )
        save_credit_trajectory_payload(
            payload,
            base_dir=self.base_dir,
            validate=False,
        )
        return payload

    def save_profile(self, **kwargs: Any) -> Dict[str, Any]:
        return self.save_credit_trajectory(**kwargs)

    def load_credit_trajectory(
        self,
        entity_ref: str,
        as_of_date: Any,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return load_credit_trajectory_payload(
            entity_ref,
            as_of_date,
            base_dir=self.base_dir,
            validate=validate,
        )

    def load_profile(
        self,
        entity_ref: str,
        as_of_date: Any,
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        return self.load_credit_trajectory(entity_ref, as_of_date, validate=validate)

    def credit_trajectory_exists(self, entity_ref: str, as_of_date: Any) -> bool:
        return self.storage_path(entity_ref, as_of_date).exists()

    def profile_exists(self, entity_ref: str, as_of_date: Any) -> bool:
        return self.credit_trajectory_exists(entity_ref, as_of_date)

    def list_credit_trajectories(self, entity_ref: str) -> List[str]:
        entity_dir = self.base_dir / _safe_segment(entity_ref)
        if not entity_dir.exists():
            return []
        return sorted(p.stem for p in entity_dir.glob("*.json"))

    def list_profiles(self, entity_ref: str) -> List[str]:
        return self.list_credit_trajectories(entity_ref)


__all__ = [
    "build_credit_trajectory_payload",
    "save_credit_trajectory_payload",
    "load_credit_trajectory_payload",
    "CreditTrajectoryStore",
]