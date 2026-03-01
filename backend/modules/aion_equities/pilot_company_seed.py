from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


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
    return Path(__file__).resolve().parent / "data" / "pilot_company_seed"


def company_seed_storage_path(
    company_id: str,
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    root = Path(base_dir) if base_dir is not None else _default_storage_dir()
    return root / f"{_safe_segment(company_id)}.json"


def build_company_seed_payload(
    *,
    company_id: str,
    ticker: str,
    name: str,
    sector: str,
    country: str,
    generated_by: str = "aion_equities.pilot_company_seed",
    payload_patch: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    now = _utc_now_iso()

    payload: Dict[str, Any] = {
        "company_id": str(company_id),
        "ticker": str(ticker),
        "name": str(name),
        "sector": str(sector),
        "country": str(country),
        "seed_status": "active",
        "created_at": now,
        "updated_at": now,
        "generated_by": str(generated_by),
        "sector_template_ref": None,
        "fingerprint_ref": None,
        "credit_profile_ref": None,
        "pair_context_ref": None,
        "country_context_ref": None,
        "predictability_profile": {
            "acs_band": "medium",
            "sector_confidence_tier": "tier_2",
        },
        "runtime_hooks": {
            "trigger_feed_profile": [],
            "next_expected_report_window": None,
        },
    }

    if payload_patch:
        payload = _deep_merge(payload, payload_patch)

    payload["company_id"] = str(payload["company_id"])
    payload["ticker"] = str(payload["ticker"])
    payload["name"] = str(payload["name"])
    payload["sector"] = str(payload["sector"])
    payload["country"] = str(payload["country"])
    payload["updated_at"] = _utc_now_iso()

    if not isinstance(payload.get("predictability_profile"), dict):
        payload["predictability_profile"] = {
            "acs_band": "medium",
            "sector_confidence_tier": "tier_2",
        }

    predictability_profile = payload["predictability_profile"]
    predictability_profile["acs_band"] = str(
        predictability_profile.get("acs_band", "medium")
    ).strip().lower() or "medium"
    predictability_profile["sector_confidence_tier"] = str(
        predictability_profile.get("sector_confidence_tier", "tier_2")
    ).strip().lower() or "tier_2"

    if not isinstance(payload.get("runtime_hooks"), dict):
        payload["runtime_hooks"] = {
            "trigger_feed_profile": [],
            "next_expected_report_window": None,
        }

    runtime_hooks = payload["runtime_hooks"]
    trigger_feed_profile = runtime_hooks.get("trigger_feed_profile", [])
    if not isinstance(trigger_feed_profile, list):
        trigger_feed_profile = [trigger_feed_profile]
    runtime_hooks["trigger_feed_profile"] = trigger_feed_profile

    return payload


def save_company_seed_payload(
    payload: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    path = company_seed_storage_path(
        payload["company_id"],
        base_dir=base_dir,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_company_seed_payload(
    company_id: str,
    *,
    base_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    path = company_seed_storage_path(company_id, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Pilot company seed not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


class PilotCompanySeedStore:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir) / "pilot_company_seed"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def storage_path(self, company_id: str) -> Path:
        return company_seed_storage_path(company_id, base_dir=self.base_dir)

    def _build_payload_patch_from_kwargs(
        self,
        *,
        payload_patch: Optional[Dict[str, Any]] = None,
        legacy_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        patch = deepcopy(payload_patch or {})
        legacy_kwargs = dict(legacy_kwargs or {})

        company_ref = legacy_kwargs.pop("company_ref", None)
        validate = legacy_kwargs.pop("validate", None)
        _ = validate  # accepted but intentionally unused

        if company_ref and "company_ref" not in patch:
            patch["company_ref"] = company_ref

        top_level_fields = [
            "seed_status",
            "sector_template_ref",
            "fingerprint_ref",
            "credit_profile_ref",
            "pair_context_ref",
            "country_context_ref",
        ]
        for field in top_level_fields:
            if field in legacy_kwargs and legacy_kwargs[field] is not None:
                patch[field] = deepcopy(legacy_kwargs.pop(field))

        if "predictability_profile" in legacy_kwargs and legacy_kwargs["predictability_profile"] is not None:
            incoming_predictability = deepcopy(legacy_kwargs.pop("predictability_profile"))
            existing_predictability = deepcopy(patch.get("predictability_profile", {}))
            if isinstance(incoming_predictability, dict):
                patch["predictability_profile"] = _deep_merge(
                    existing_predictability,
                    incoming_predictability,
                )
            else:
                patch["predictability_profile"] = existing_predictability

        if "runtime_hooks" in legacy_kwargs and legacy_kwargs["runtime_hooks"] is not None:
            incoming_runtime_hooks = deepcopy(legacy_kwargs.pop("runtime_hooks"))
            existing_runtime_hooks = deepcopy(patch.get("runtime_hooks", {}))
            if isinstance(incoming_runtime_hooks, dict):
                patch["runtime_hooks"] = _deep_merge(
                    existing_runtime_hooks,
                    incoming_runtime_hooks,
                )

        trigger_feed_profile = legacy_kwargs.pop("trigger_feed_profile", None)
        next_expected_report_window = legacy_kwargs.pop("next_expected_report_window", None)
        if trigger_feed_profile is not None or next_expected_report_window is not None:
            existing_runtime_hooks = deepcopy(patch.get("runtime_hooks", {}))
            runtime_patch: Dict[str, Any] = {}
            if trigger_feed_profile is not None:
                runtime_patch["trigger_feed_profile"] = deepcopy(trigger_feed_profile)
            if next_expected_report_window is not None:
                runtime_patch["next_expected_report_window"] = deepcopy(next_expected_report_window)
            patch["runtime_hooks"] = _deep_merge(existing_runtime_hooks, runtime_patch)

        if legacy_kwargs:
            patch = _deep_merge(patch, legacy_kwargs)

        return patch or None

    def save_seed(
        self,
        *,
        company_id: str,
        ticker: str,
        name: str,
        sector: str,
        country: str,
        generated_by: str = "aion_equities.pilot_company_seed",
        payload_patch: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        merged_patch = self._build_payload_patch_from_kwargs(
            payload_patch=payload_patch,
            legacy_kwargs=kwargs,
        )
        payload = build_company_seed_payload(
            company_id=company_id,
            ticker=ticker,
            name=name,
            sector=sector,
            country=country,
            generated_by=generated_by,
            payload_patch=merged_patch,
        )
        save_company_seed_payload(payload, base_dir=self.base_dir)
        return payload

    def save_company_seed(
        self,
        *,
        company_id: str,
        ticker: str,
        name: str,
        sector: str,
        country: str,
        generated_by: str = "aion_equities.pilot_company_seed",
        payload_patch: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return self.save_seed(
            company_id=company_id,
            ticker=ticker,
            name=name,
            sector=sector,
            country=country,
            generated_by=generated_by,
            payload_patch=payload_patch,
            **kwargs,
        )

    def load_seed(self, company_id: str) -> Dict[str, Any]:
        return load_company_seed_payload(company_id, base_dir=self.base_dir)

    def load_company_seed(self, company_id: str) -> Dict[str, Any]:
        return self.load_seed(company_id)

    def seed_exists(self, company_id: str) -> bool:
        return self.storage_path(company_id).exists()

    def company_seed_exists(self, company_id: str) -> bool:
        return self.seed_exists(company_id)

    def list_company_ids(self) -> List[str]:
        return sorted(p.stem.replace("_", "/") for p in self.base_dir.glob("*.json"))


__all__ = [
    "build_company_seed_payload",
    "save_company_seed_payload",
    "load_company_seed_payload",
    "PilotCompanySeedStore",
]