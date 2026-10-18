from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.modules.aion_business.runtime.business_data_discovery import load_manifest
from backend.modules.aion_business.runtime.business_data_domain_registry import (
    BusinessDataDomainRegistry,
)


SCENARIO_CATALOGUE_SCHEMA = "tessaris.business-data-discovery-scenarios.v1"
ALLOWED_EXECUTION_SURFACES = {
    "desktop_renderer", "electron_main", "desktop_backend", "provider_sandbox",
    "mobile_companion", "filesystem_import", "update_runner",
}
ALLOWED_EXTERNAL_CLASSES = {
    "none", "secret_store", "provider_api", "customer_export", "backup_destination",
    "billing_control_plane", "notification_provider",
}


class BusinessDataDiscoveryScenarioError(ValueError):
    pass


def load_discovery_scenario_catalogue(
    *, catalogue_path: str | Path, manifest_path: str | Path
) -> dict[str, Any]:
    try:
        catalogue = json.loads(Path(catalogue_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BusinessDataDiscoveryScenarioError("discovery_scenario_catalogue_invalid") from exc
    if catalogue.get("schema_version") != SCENARIO_CATALOGUE_SCHEMA:
        raise BusinessDataDiscoveryScenarioError("discovery_scenario_catalogue_schema_invalid")
    manifest = load_manifest(Path(manifest_path))
    required = {str(item["id"]) for item in manifest["required_discovery_sessions"]}
    registered_domains = set(BusinessDataDomainRegistry().manifest())
    rows = catalogue.get("scenarios")
    if not isinstance(rows, list):
        raise BusinessDataDiscoveryScenarioError("discovery_scenarios_missing")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise BusinessDataDiscoveryScenarioError("discovery_scenario_invalid")
        session_id = str(row.get("session_id") or "")
        if session_id in indexed or session_id not in required:
            raise BusinessDataDiscoveryScenarioError(
                f"discovery_scenario_session_invalid:{session_id}"
            )
        surfaces = set(row.get("execution_surfaces") or [])
        external = set(row.get("expected_external_classes") or [])
        domains = set(row.get("expected_domains") or [])
        if not surfaces or not surfaces <= ALLOWED_EXECUTION_SURFACES:
            raise BusinessDataDiscoveryScenarioError(
                f"discovery_scenario_surfaces_invalid:{session_id}"
            )
        if not external or not external <= ALLOWED_EXTERNAL_CLASSES:
            raise BusinessDataDiscoveryScenarioError(
                f"discovery_scenario_external_class_invalid:{session_id}"
            )
        if not domains or not domains <= registered_domains:
            raise BusinessDataDiscoveryScenarioError(
                f"discovery_scenario_domains_invalid:{session_id}"
            )
        if not row.get("journey_steps") or not row.get("completion_assertions"):
            raise BusinessDataDiscoveryScenarioError(
                f"discovery_scenario_evidence_missing:{session_id}"
            )
        indexed[session_id] = row
    missing = sorted(required - set(indexed))
    if missing:
        raise BusinessDataDiscoveryScenarioError(
            "discovery_scenarios_missing_sessions:" + ",".join(missing)
        )
    return {
        "schema_version": SCENARIO_CATALOGUE_SCHEMA,
        "scenario_count": len(indexed),
        "required_session_count": len(required),
        "complete": set(indexed) == required,
        "scenarios": [indexed[key] for key in sorted(indexed)],
    }
