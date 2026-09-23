"""Governed creative publication packages and real campaign outcome evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.modules.aion_business.runtime.local_asset_store import LocalAssetStore
from backend.modules.aion_business.runtime.marketing_connection_service import MarketingConnectionService


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class CreativePublicationService:
    CHANNELS = {"instagram", "facebook", "linkedin", "tiktok", "youtube", "google_ads", "meta_ads"}
    MODES = {"organic", "paid"}

    def __init__(self, asset_store: LocalAssetStore | None = None) -> None:
        self.assets = asset_store or LocalAssetStore()

    def _root(self, workspace_id: str) -> Path:
        marketing = self.assets.ensure_workspace_dirs(workspace_id)["marketing"]
        return self.assets.ensure_dir(marketing / "publication_packages")

    def _path(self, workspace_id: str, package_id: str) -> Path:
        return self._root(workspace_id) / f"{self.assets._sanitize_run_id(package_id)}.json"

    @staticmethod
    def _contract(record: dict[str, Any]) -> dict[str, Any]:
        return {key: record[key] for key in (
            "id", "workspace_id", "asset_path", "asset_sha256", "channel", "mode",
            "caption", "call_to_action", "scheduled_for", "daily_budget_eur", "campaign_name",
        )}

    @staticmethod
    def _connector_readiness(workspace_id: str, channel: str, mode: str) -> dict[str, Any]:
        provider = "meta" if channel in {"instagram", "facebook", "meta_ads"} else channel
        status = MarketingConnectionService().status(workspace_id, provider)
        required_tier = "advertising" if mode == "paid" or channel in {"meta_ads", "google_ads"} else "organic"
        tier_order = {"analytics": 0, "organic": 1, "advertising": 2}
        missing = []
        if not status["connected"]: missing.append("customer_oauth_connection")
        selected = status["selected_accounts"]
        required_account_kind = "ad_account" if channel == "meta_ads" else (
            "instagram" if channel == "instagram" else ("page" if channel == "facebook" else "primary")
        )
        if provider == "google_ads": required_account_kind = "customer"
        if provider == "youtube": required_account_kind = "channel"
        if provider == "linkedin": required_account_kind = "member"
        if provider == "tiktok": required_account_kind = "creator"
        if not selected.get(required_account_kind): missing.append(f"{required_account_kind}_selection")
        if tier_order.get(status["permission_tier"], 0) < tier_order[required_tier]: missing.append(f"{required_tier}_permission")
        return {
            "provider": provider, "required_permission_tier": required_tier,
            "required_account_kind": required_account_kind, "missing_credentials": missing,
            "connected": not missing, "validate_only_supported": channel in {"google_ads", "meta_ads"},
            "customer_owned_connection": True, "external_writes_enabled": False,
        }

    def prepare(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        asset = Path(str(payload.get("asset_path") or "")).expanduser().resolve()
        if not asset.is_file():
            raise ValueError("publication_asset_not_found")
        channel = str(payload.get("channel") or "instagram").strip().lower()
        if channel not in self.CHANNELS:
            raise ValueError("unsupported_publication_channel")
        mode = str(payload.get("mode") or "organic").strip().lower()
        if mode not in self.MODES:
            raise ValueError("unsupported_publication_mode")
        caption = str(payload.get("caption") or "").strip()
        if not caption:
            raise ValueError("publication_caption_required")
        daily_budget = max(0.0, float(payload.get("daily_budget_eur") or 0))
        if mode == "paid" and daily_budget <= 0:
            raise ValueError("paid_campaign_requires_positive_daily_budget")
        if mode == "organic":
            daily_budget = 0.0
        package_id = f"publication_{uuid4().hex[:16]}"
        data = asset.read_bytes()
        record = {
            "id": package_id, "workspace_id": workspace_id, "asset_path": str(asset),
            "asset_sha256": hashlib.sha256(data).hexdigest(), "asset_bytes": len(data),
            "channel": channel, "mode": mode, "caption": caption,
            "call_to_action": str(payload.get("call_to_action") or "Learn more").strip(),
            "scheduled_for": str(payload.get("scheduled_for") or "").strip() or None,
            "daily_budget_eur": daily_budget,
            "campaign_name": str(payload.get("campaign_name") or "Tessaris campaign").strip(),
            "connector": self._connector_readiness(workspace_id, channel, mode),
            "status": "prepared", "approval": None, "outcomes": [],
            "created_at": _now(), "created_by_person_id": str(payload.get("created_by_person_id") or "desktop_user"),
            "external_execution_available": False,
            "external_execution_boundary": "Connector credentials and a separate exact execution approval are required.",
        }
        record["approval_hash"] = _hash(self._contract(record))
        self.assets.write_json(self._path(workspace_id, package_id), record)
        return record

    def get(self, workspace_id: str, package_id: str) -> dict[str, Any]:
        path = self._path(workspace_id, package_id)
        if not path.is_file():
            raise FileNotFoundError("creative_publication_package_not_found")
        return json.loads(path.read_text(encoding="utf-8"))

    def approve(self, workspace_id: str, package_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = self.get(workspace_id, package_id)
        if record["status"] != "prepared":
            raise ValueError("only_prepared_publication_packages_can_be_approved")
        expected = str(payload.get("expected_approval_hash") or "")
        if expected != record["approval_hash"] or expected != _hash(self._contract(record)):
            raise PermissionError("publication_package_changed_since_review")
        if payload.get("external_publish_authorized") is not True:
            raise PermissionError("external_publication_requires_explicit_authority")
        ceiling = max(0.0, float(payload.get("maximum_total_spend_eur") or 0))
        if record["mode"] == "paid" and ceiling <= 0:
            raise ValueError("paid_publication_requires_total_spend_ceiling")
        record["approval"] = {
            "approved_by_person_id": str(payload.get("approved_by_person_id") or ""),
            "approved_at": _now(), "approved_hash": expected,
            "maximum_total_spend_eur": ceiling, "external_publish_authorized": True,
        }
        record["status"] = "approved_waiting_connector" if not record["connector"]["connected"] else "approved_ready_for_validate_only"
        self.assets.write_json(self._path(workspace_id, package_id), record)
        return record

    def record_outcome(self, workspace_id: str, package_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = self.get(workspace_id, package_id)
        impressions = max(0, int(payload.get("impressions") or 0))
        clicks = max(0, int(payload.get("clicks") or 0))
        qualified_actions = max(0, int(payload.get("qualified_actions") or 0))
        conversions = max(0, int(payload.get("conversions") or 0))
        spend = max(0.0, float(payload.get("spend_eur") or 0))
        revenue = max(0.0, float(payload.get("revenue_eur") or 0))
        complaints = max(0, int(payload.get("complaints") or 0))
        false_claims = max(0, int(payload.get("false_or_unsafe_claims") or 0))
        evidence = {
            "recorded_at": _now(), "source": str(payload.get("source") or "manual_verified"),
            "impressions": impressions, "clicks": clicks, "qualified_actions": qualified_actions,
            "conversions": conversions, "spend_eur": spend, "revenue_eur": revenue,
            "complaints": complaints, "false_or_unsafe_claims": false_claims,
            "ctr": clicks / impressions if impressions else None,
            "qualified_action_rate": qualified_actions / impressions if impressions else None,
            "conversion_rate": conversions / clicks if clicks else None,
            "cost_per_qualified_action": spend / qualified_actions if qualified_actions else None,
            "roas": revenue / spend if spend else None,
            "safe": false_claims == 0,
        }
        record["outcomes"].append(evidence)
        record["latest_outcome"] = evidence
        record["status"] = "measured_safe" if evidence["safe"] else "measurement_escalated"
        self.assets.write_json(self._path(workspace_id, package_id), record)
        return record
