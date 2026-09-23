from __future__ import annotations

import json
import zipfile

from backend.modules.aion_business.runtime.capability_packages import CapabilityPackageAuthority
from scripts.build_core_capability_pack_library import build_library


def test_library_builds_five_distinct_signed_least_authority_packs(tmp_path):
    result = build_library(tmp_path / "library")
    assert len(result["packages"]) == 5
    assert {row["package_ref"] for row in result["packages"]} == {
        "aion.marketing.marketing_content@1.0.0",
        "aion.customer_support.customer_support_triage@1.0.0",
        "aion.finance_monitoring.finance_monitoring@1.0.0",
        "aion.operations.operations_coordination@1.0.0",
        "aion.operations.field_services_dispatch@1.0.0",
    }
    authority = CapabilityPackageAuthority(tmp_path / "registry", trusted_publishers=[result["index"]["publisher_public_key"]])
    for row in result["packages"]:
        manifest = json.loads(row["manifest"].read_text())
        installed = authority.install(manifest, row["artifact"])
        assert installed["status"] == "installed_unqualified"
        assert manifest["permissions"]["network_hosts"] == []
        assert manifest["contains_customer_data"] is False


def test_each_pack_has_tailored_policy_procedure_and_no_credentials(tmp_path):
    result = build_library(tmp_path / "library")
    purposes = set()
    for row in result["packages"]:
        with zipfile.ZipFile(row["artifact"]) as archive:
            procedure = json.loads(archive.read("procedure/v1.json"))
            policy = json.loads(archive.read("policy/v1.json"))
            tools = json.loads(archive.read("tools/v1.json"))
            purposes.add(procedure["purpose"])
            assert procedure["default_mode"] == "prepare_for_review"
            assert policy["model_may_not_write_canonical_memory"] is True
            assert tools["bundles_credentials"] is False
            assert tools["requires_authorized_adapter"] is True
    assert len(purposes) == 5


def test_library_is_byte_reproducible_even_when_development_signature_changes(tmp_path):
    first = build_library(tmp_path / "one")
    second = build_library(tmp_path / "two")
    first_bytes = [row["artifact"].read_bytes() for row in first["packages"]]
    second_bytes = [row["artifact"].read_bytes() for row in second["packages"]]
    assert first_bytes == second_bytes
