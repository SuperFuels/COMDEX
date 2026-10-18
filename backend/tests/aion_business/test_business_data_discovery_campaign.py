from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.modules.aion_business.runtime.business_data_discovery_campaign import (
    BusinessDataDiscoveryCampaignError,
    build_discovery_campaign_status,
    run_discovery_session,
)


ACTIVE_DESTINATION: Path | None = None


def _write_to_active_destination() -> None:
    assert ACTIVE_DESTINATION is not None
    ACTIVE_DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_DESTINATION.write_text("synthetic-value", encoding="utf-8")


def _write_then_fail() -> None:
    _write_to_active_destination()
    raise RuntimeError("synthetic private-looking failure detail")


def _manifest(path: Path) -> Path:
    path.write_text(json.dumps({
        "schema_version": "tessaris.business-data-manifest.v1",
        "required_discovery_sessions": [
            {"id": "onboarding", "name": "Onboarding", "status": "required"},
            {"id": "file-cabinet", "name": "File Cabinet", "status": "required"},
        ],
        "touchpoints": [],
    }), encoding="utf-8")
    return path


def _catalogue(path: Path) -> Path:
    path.write_text(json.dumps({
        "schema_version": "tessaris.business-data-discovery-scenarios.v1",
        "privacy": "synthetic",
        "scenarios": [{
            "session_id": session,
            "execution_surfaces": ["desktop_backend"],
            "journey_steps": ["write synthetic Vault record"],
            "expected_domains": ["business.identity"],
            "expected_external_classes": ["none"],
            "completion_assertions": ["write completed"],
        } for session in ("onboarding", "file-cabinet")],
    }), encoding="utf-8")
    return path


def test_backend_runner_emits_fragment_without_falsely_passing_whole_campaign(tmp_path):
    global ACTIVE_DESTINATION
    manifest = _manifest(tmp_path / "manifest.json")
    catalogue = _catalogue(tmp_path / "scenarios.json")
    trace_root = tmp_path / "traces"
    ACTIVE_DESTINATION = tmp_path / "vault" / "onboarding.json"
    report = run_discovery_session(
        manifest_path=manifest,
        scenario_catalogue_path=catalogue,
        trace_root=trace_root,
        session_id="onboarding",
        scenario="founder-onboarding-save",
        scenario_callable=_write_to_active_destination,
        source_root=Path(__file__).resolve().parents[3],
        application_root=tmp_path / "app",
        update_root=tmp_path / "updates",
        vault_roots=[tmp_path / "vault"],
        path_fingerprint_key=b"campaign-fingerprint-secret-32-bytes!!",
    )
    assert report["release_gate_passed"] is True
    status = build_discovery_campaign_status(
        manifest_path=manifest, trace_root=trace_root
    )
    assert status["passed_session_count"] == 0
    assert status["missing_session_count"] == 2
    assert status["campaign_ready"] is False
    encoded = json.dumps(status)
    assert str(tmp_path) not in encoded
    assert "synthetic-value" not in encoded


def test_campaign_retains_opaque_failed_evidence_and_never_marks_it_passed(tmp_path):
    global ACTIVE_DESTINATION
    manifest = _manifest(tmp_path / "manifest.json")
    catalogue = _catalogue(tmp_path / "scenarios.json")
    trace_root = tmp_path / "traces"
    ACTIVE_DESTINATION = tmp_path / "vault" / "onboarding.json"
    with pytest.raises(BusinessDataDiscoveryCampaignError, match="discovery_scenario_failed:onboarding"):
        run_discovery_session(
            manifest_path=manifest,
            scenario_catalogue_path=catalogue,
            trace_root=trace_root,
            session_id="onboarding",
            scenario="failed-onboarding",
            scenario_callable=_write_then_fail,
            source_root=Path(__file__).resolve().parents[3],
            application_root=tmp_path / "app",
            update_root=tmp_path / "updates",
            vault_roots=[tmp_path / "vault"],
            path_fingerprint_key=b"campaign-fingerprint-secret-32-bytes!!",
        )
    raw = (trace_root / "onboarding.desktop_backend.json").read_text(encoding="utf-8")
    assert "synthetic private-looking failure detail" not in raw
    status = build_discovery_campaign_status(manifest_path=manifest, trace_root=trace_root)
    assert status["failed_session_count"] == 0
    assert status["missing_session_count"] == 2
    assert status["campaign_ready"] is False


def test_runner_labels_only_catalogued_python_surface(tmp_path):
    global ACTIVE_DESTINATION
    manifest = _manifest(tmp_path / "manifest.json")
    catalogue = tmp_path / "scenarios.json"
    catalogue.write_text(json.dumps({
        "schema_version": "tessaris.business-data-discovery-scenarios.v1",
        "privacy": "synthetic",
        "scenarios": [
            {
                "session_id": "onboarding",
                "execution_surfaces": ["filesystem_import"],
                "journey_steps": ["import synthetic file"],
                "expected_domains": ["business.identity"],
                "expected_external_classes": ["none"],
                "completion_assertions": ["import completed"],
            },
            {
                "session_id": "file-cabinet",
                "execution_surfaces": ["desktop_backend"],
                "journey_steps": ["save file"],
                "expected_domains": ["file_cabinet.tree"],
                "expected_external_classes": ["none"],
                "completion_assertions": ["save completed"],
            },
        ],
    }), encoding="utf-8")
    trace_root = tmp_path / "traces"
    ACTIVE_DESTINATION = tmp_path / "vault" / "imported.json"
    report = run_discovery_session(
        manifest_path=manifest,
        scenario_catalogue_path=catalogue,
        trace_root=trace_root,
        session_id="onboarding",
        scenario="synthetic-import",
        scenario_callable=_write_to_active_destination,
        source_root=Path(__file__).resolve().parents[3],
        application_root=tmp_path / "app",
        update_root=tmp_path / "updates",
        vault_roots=[tmp_path / "vault"],
        path_fingerprint_key=b"campaign-fingerprint-secret-32-bytes!!",
        surface="filesystem_import",
    )
    assert report["surface"] == "filesystem_import"
    assert (trace_root / "onboarding.filesystem_import.json").is_file()
    with pytest.raises(BusinessDataDiscoveryCampaignError, match="not_python_instrumented"):
        run_discovery_session(
            manifest_path=manifest,
            scenario_catalogue_path=catalogue,
            trace_root=trace_root,
            session_id="onboarding",
            scenario="synthetic-provider",
            scenario_callable=_write_to_active_destination,
            source_root=Path(__file__).resolve().parents[3],
            application_root=tmp_path / "app",
            update_root=tmp_path / "updates",
            vault_roots=[tmp_path / "vault"],
            path_fingerprint_key=b"campaign-fingerprint-secret-32-bytes!!",
            surface="provider_sandbox",
        )


def test_runner_accepts_explicit_secret_store_boundary(tmp_path):
    global ACTIVE_DESTINATION
    manifest = _manifest(tmp_path / "manifest.json")
    catalogue = _catalogue(tmp_path / "scenarios.json")
    trace_root = tmp_path / "traces"
    ACTIVE_DESTINATION = tmp_path / "security" / "legal-key.bin"
    report = run_discovery_session(
        manifest_path=manifest,
        scenario_catalogue_path=catalogue,
        trace_root=trace_root,
        session_id="onboarding",
        scenario="secret-store-write",
        scenario_callable=_write_to_active_destination,
        source_root=Path(__file__).resolve().parents[3],
        application_root=tmp_path / "app",
        update_root=tmp_path / "updates",
        vault_roots=[tmp_path / "vault"],
        secret_store_roots=[tmp_path / "security"],
        path_fingerprint_key=b"campaign-fingerprint-secret-32-bytes!!",
    )
    assert set(report["destination_counts"]) == {"secret_store"}
    assert report["destination_counts"]["secret_store"] >= 1
    assert report["release_gate_passed"] is True
