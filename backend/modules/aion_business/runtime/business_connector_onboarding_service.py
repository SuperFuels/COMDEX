from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any, Callable, Dict

from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import WorkflowFileCabinetRepository
from backend.modules.aion_fabric.canonical import canonical_hash, utc_now_iso


CONNECTOR_ONBOARDING_VERSION = "aion.business_connector_onboarding.v1"


class BusinessConnectorOnboardingService:
    """One secret-free view over existing business connector authorities."""

    def __init__(
        self,
        *,
        business_root: str | Path | None = None,
        file_loader: Callable[[str], Dict[str, Any]] | None = None,
        google_probe: Callable[[], Dict[str, Any]] | None = None,
        crm_probe: Callable[[], Dict[str, Any]] | None = None,
        xero_probe: Callable[[str], Dict[str, Any]] | None = None,
    ) -> None:
        self.business_root = Path(business_root) if business_root else AIONBusinessPaths.BUSINESS_CONTAINERS
        self.file_loader = file_loader or WorkflowFileCabinetRepository.load
        self.google_probe = google_probe or self._google_status
        self.crm_probe = crm_probe or self._crm_status
        self.xero_probe = xero_probe or self._xero_status

    @staticmethod
    def _google_status() -> Dict[str, Any]:
        from backend.api.local_node_router import get_runtime

        runtime = get_runtime()
        health = runtime.get_gmail_connector_health()
        config = runtime.connector_registry.get_gmail_config()
        return {
            **health,
            "scopes": list(config.get("oauth_scopes") or []),
            "token_present": runtime.connector_registry.has_gmail_token_reference(),
        }

    @staticmethod
    def _crm_status() -> Dict[str, Any]:
        from backend.api.local_node_router import get_runtime

        return get_runtime().get_hubspot_connector_health()

    @staticmethod
    def _xero_status(business_id: str) -> Dict[str, Any]:
        from backend.modules.aion_business.api.finance_integrations_api import xero_status

        return dict(xero_status(business_id).get("connection") or {})

    @staticmethod
    def _public_error(provider: str, exc: Exception) -> Dict[str, Any]:
        return {
            "provider": provider,
            "connected": False,
            "status": "unavailable",
            "reason": type(exc).__name__,
        }

    @staticmethod
    def _nodes(tree: Dict[str, Any]) -> list[Dict[str, Any]]:
        root = tree.get("folders") or (tree.get("root") or {}).get("children") or []
        return [item for item in WorkflowFileCabinetRepository._walk(root)]

    def _sales_projection(self, business_id: str) -> Dict[str, Any]:
        root = self.business_root / business_id / "sales" / "revenue_spine"
        opportunity_dir = root / "opportunities"
        opportunities = []
        for path in sorted(opportunity_dir.glob("*.json")) if opportunity_dir.exists() else []:
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(value, dict):
                    opportunities.append(value)
            except (OSError, ValueError):
                continue
        source_counts = Counter(str(item.get("source") or "unknown").lower() for item in opportunities)
        stage_counts = Counter(str(item.get("stage") or "unknown").lower() for item in opportunities)
        gmail_count = sum(count for source, count in source_counts.items() if "gmail" in source or "email" in source)
        crm_count = sum(count for source, count in source_counts.items() if "hubspot" in source or "crm" in source)
        calendar_count = sum(1 for item in opportunities if item.get("appointment") or item.get("booking"))
        return {
            "opportunity_count": len(opportunities),
            "gmail_evidence_count": gmail_count,
            "crm_evidence_count": crm_count,
            "calendar_evidence_count": calendar_count,
            "stage_counts": dict(sorted(stage_counts.items())),
            "contains_contact_details": False,
            "projection_hash": canonical_hash({
                "opportunity_count": len(opportunities),
                "source_counts": dict(sorted(source_counts.items())),
                "stage_counts": dict(sorted(stage_counts.items())),
            }),
        }

    def snapshot(self, candidate: str) -> Dict[str, Any]:
        business_id = canonical_business_id(candidate)
        try:
            tree = self.file_loader(business_id)
            nodes = self._nodes(tree)
            files = {
                "provider": "local_files",
                "connected": True,
                "status": "ready",
                "item_count": len(nodes),
                "document_count": sum(item.get("type") != "folder" for item in nodes),
                "protected_record_count": sum(WorkflowFileCabinetRepository.protection(item)["protected"] for item in nodes),
            }
        except Exception as exc:
            files = self._public_error("local_files", exc)
        try:
            google = self.google_probe()
        except Exception as exc:
            google = self._public_error("google", exc)
        try:
            crm = self.crm_probe()
        except Exception as exc:
            crm = self._public_error("hubspot", exc)
        try:
            xero = self.xero_probe(business_id)
        except Exception as exc:
            xero = self._public_error("xero", exc)

        scopes = set(str(item) for item in google.get("scopes") or [])
        google_connected = str(google.get("auth_status") or google.get("status") or "") == "connected" and google.get("token_present") is True
        calendar_scope = any("calendar" in scope for scope in scopes)
        sales_projection = self._sales_projection(business_id)
        cards = [
            self._card("files", "Files", files.get("connected") is True, files.get("status"), files,
                       target="business_knowledge + workflow_file_cabinet", projection={"document_count": files.get("document_count", 0), "protected_record_count": files.get("protected_record_count", 0)},
                       connect={"method": "open_local_surface", "target": "file_cabinet"}),
            self._card("gmail", "Gmail", google_connected, google.get("connector_health") or google.get("status"), google,
                       target="sales_revenue_spine", projection={"imported_enquiry_count": sales_projection["gmail_evidence_count"]},
                       connect={"method": "open_external_oauth", "endpoint": "/api/local-node/connectors/gmail/connect-url", "http_method": "GET"}),
            self._card("calendar", "Google Calendar", google_connected and calendar_scope, "connected" if google_connected and calendar_scope else "scope_not_connected", google,
                       target="sales_revenue_spine + calendar_planning", projection={"appointment_evidence_count": sales_projection["calendar_evidence_count"]},
                       connect={"method": "open_external_oauth", "endpoint": "/api/local-node/connectors/gmail/connect-url", "http_method": "GET", "shared_google_authorization": True}),
            self._card("crm_sales", "CRM / Sales", str(crm.get("auth_status") or "") == "connected", crm.get("connector_health") or crm.get("status"), crm,
                       target="sales_revenue_spine + department_intelligence.sales", projection={"crm_opportunity_count": sales_projection["crm_evidence_count"], "pipeline_stage_counts": sales_projection["stage_counts"]},
                       connect={"method": "open_external_oauth", "endpoint": "/api/local-node/connectors/hubspot/mcp/connect-url", "http_method": "GET"}),
            self._card("xero", "Xero", xero.get("connected") is True, xero.get("status"), xero,
                       target="business_financial_model", projection={"last_sync_status": xero.get("last_sync_status") or "never_synced", "sync_summary": xero.get("sync_summary") or {}},
                       connect={"method": "open_external_oauth", "endpoint": f"/api/aion/integrations/xero/{business_id}/connect", "http_method": "POST"}),
        ]
        return {
            "ok": True,
            "schema_version": CONNECTOR_ONBOARDING_VERSION,
            "business_id": business_id,
            "cards": cards,
            "connected_count": sum(card["connected"] for card in cards),
            "total_count": len(cards),
            "sales_projection": sales_projection,
            "privacy": {
                "credentials_exposed": False,
                "raw_messages_exposed": False,
                "contact_details_exposed": False,
                "calendar_titles_exposed": False,
                "bank_details_exposed": False,
            },
            "external_write_performed": False,
            "generated_at": utc_now_iso(),
        }

    @staticmethod
    def _card(connector_id: str, label: str, connected: bool, status: Any, health: Dict[str, Any], *, target: str, projection: Dict[str, Any], connect: Dict[str, Any]) -> Dict[str, Any]:
        safe_health = {
            key: health.get(key)
            for key in ("provider", "auth_status", "connector_health", "status", "last_poll_at", "last_poll_status", "last_sync_at", "last_sync_status", "last_error", "dry_run_only", "read_only")
            if key in health
        }
        return {
            "connector_id": connector_id,
            "label": label,
            "connected": bool(connected),
            "status": str(status or ("connected" if connected else "not_connected")),
            "health": safe_health,
            "projection": {
                "target": target,
                "summary": projection,
                "review_required_before_business_truth": connector_id in {"files", "gmail", "crm_sales"},
                "raw_provider_data_is_not_business_map_truth": True,
            },
            "connect": connect,
            "read_only_onboarding": True,
            "credentials_exposed": False,
        }
