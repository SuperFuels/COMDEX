from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.glyphchain_release_readiness import (
    EVIDENCE_SCHEMA,
    TASKS,
    TRUST_ROOTS_SCHEMA,
    GlyphChainReleaseReadinessError,
    GlyphChainReleaseReadinessEvaluator,
    sign_evidence,
    sign_trust_root_inventory,
)
RELEASE = "ab" * 32
ROOT = Path(__file__).resolve().parents[3]


def _key_root(role: str, *, independent: bool = False):
    key = Ed25519PrivateKey.generate()
    return key, {
        "public_key_base64": base64.b64encode(key.public_key().public_bytes_raw()).decode("ascii"),
        "roles": [role], "independent": independent,
    }


def _body(task_id: str, *, release: str = RELEASE):
    artifacts = [
        {
            "artifact_id": f"{task_id.lower()}:{index}",
            "kind": kind,
            "sha256": f"{index + 1:02x}" * 32,
        }
        for index, kind in enumerate(TASKS[task_id]["required_artifact_kinds"])
    ]
    return {
        "schema_version": EVIDENCE_SCHEMA,
        "task_id": task_id,
        "release_manifest_sha256": release,
        "environment": "production",
        "result": "PASS",
        "observed_at": "2026-09-26T14:00:00Z",
        "statement": f"External evidence retained for {task_id}",
        "artifacts": artifacts,
    }


def _entry(task_id: str, signers):
    body = _body(task_id)
    return {
        "task_id": task_id,
        "body": body,
        "attestations": [sign_evidence(body, signer_id=signer_id, private_key=key) for signer_id, key in signers],
    }


def _signed_trust_root_bytes(roots):
    governance_key = Ed25519PrivateKey.generate()
    body = {
        "schema_version": TRUST_ROOTS_SCHEMA,
        "generated_at": "2026-09-27T14:00:00Z",
        "trust_roots": roots,
        "claim_boundary": "Test authority inventory",
    }
    document = {
        **body,
        "attestation": sign_trust_root_inventory(
            body,
            authority_id="test-governance",
            private_key=governance_key,
        ),
    }
    payload = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return payload, governance_key.public_key(), hashlib.sha256(payload).hexdigest()


def test_empty_inventory_fails_closed_with_all_34_tasks_unmet():
    report = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE, evidence_entries=[], trust_roots={},
        generated_at="2026-09-27T14:00:00Z",
    )
    assert len(TASKS) == 34
    assert report["result"] == "BLOCKED_EXTERNAL_GATES"
    assert report["passed_count"] == 0 and report["unmet_count"] == 34
    assert report["production_release_authorized"] is False
    assert GlyphChainReleaseReadinessEvaluator.verify_report(report) is True


def test_written_remaining_checklist_and_machine_task_register_cannot_drift():
    checklist = (ROOT / "docs/aion/GLYPHCHAIN_LEGAL_REMAINING_BUILD_CHECKLIST.md").read_text(
        encoding="utf-8",
    )
    written_ids = re.findall(r"^- \[ \] `((?:LD|TR|NET|SEC|LEGAL|REL)-\d{2})`", checklist, re.MULTILINE)
    assert len(written_ids) == len(set(written_ids)) == 34
    assert set(written_ids) == set(TASKS)


def test_every_release_task_has_a_nonempty_unique_protocol_artifact_contract():
    for task_id, task in TASKS.items():
        kinds = task["required_artifact_kinds"]
        assert kinds, task_id
        assert len(kinds) == len(set(kinds)), task_id
        assert all(re.fullmatch(r"[a-z][a-z0-9_]*", kind) for kind in kinds), task_id


def test_release_evaluator_cli_import_is_side_effect_free():
    result = subprocess.run(
        [sys.executable, "backend/scripts/evaluate_glyphchain_legal_release_readiness.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "WaveScope" not in result.stdout + result.stderr
    assert "Registered geometry" not in result.stdout + result.stderr


def test_release_evaluator_cli_rejects_unsupported_inventory_schema_before_writing(tmp_path):
    release = tmp_path / "release.json"
    evidence = tmp_path / "evidence.json"
    roots = tmp_path / "roots.json"
    output = tmp_path / "report.json"
    release.write_text("{}\n", encoding="utf-8")
    evidence.write_text(json.dumps({"schema_version": "wrong", "evidence_entries": []}), encoding="utf-8")
    roots.write_text(json.dumps({
        "schema_version": TRUST_ROOTS_SCHEMA,
        "trust_roots": {},
    }), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "backend/scripts/evaluate_glyphchain_legal_release_readiness.py",
            "--release-manifest", str(release),
            "--evidence-inventory", str(evidence),
            "--trust-roots", str(roots),
            "--output", str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "schema is unsupported" in result.stderr
    assert not output.exists()


def test_release_evaluator_cli_refuses_symlink_inputs(tmp_path):
    release = tmp_path / "release.json"
    evidence_target = tmp_path / "evidence-target.json"
    evidence_link = tmp_path / "evidence-link.json"
    roots = tmp_path / "roots.json"
    output = tmp_path / "report.json"
    release.write_text("{}\n", encoding="utf-8")
    evidence_target.write_text(json.dumps({
        "schema_version": "tessaris.glyphchain-legal-release-evidence-inventory.v1",
        "evidence_entries": [],
    }), encoding="utf-8")
    evidence_link.symlink_to(evidence_target)
    roots.write_text(json.dumps({
        "schema_version": TRUST_ROOTS_SCHEMA,
        "trust_roots": {},
    }), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "backend/scripts/evaluate_glyphchain_legal_release_readiness.py",
            "--release-manifest", str(release),
            "--evidence-inventory", str(evidence_link),
            "--trust-roots", str(roots),
            "--output", str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "Refusing symbolic-link release evidence inventory" in result.stderr
    assert not output.exists()


def test_valid_evidence_closes_only_its_exact_release_bound_task():
    key, root = _key_root("delivery_operator")
    unauthenticated = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE,
        evidence_entries=[_entry("LD-01", [("delivery", key)])],
        trust_roots={"delivery": root},
    )
    assert unauthenticated["tasks"]["LD-01"]["passed"] is False
    assert "trust_roots_not_authenticated" in unauthenticated["tasks"]["LD-01"]["errors"]
    assert unauthenticated["global_errors"] == ["trust_roots_authentication_required"]
    report = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE,
        evidence_entries=[_entry("LD-01", [("delivery", key)])],
        trust_roots={"delivery": root},
        trust_roots_authenticated=True,
    )
    assert report["tasks"]["LD-01"]["passed"] is True
    assert report["passed_count"] == 1 and report["unmet_count"] == 33


def test_public_evaluator_authenticates_raw_trust_roots_and_rejects_spoofed_flag_boundary():
    key, root = _key_root("delivery_operator")
    payload, governance_public_key, pinned_sha256 = _signed_trust_root_bytes({
        "delivery": root,
    })
    report = GlyphChainReleaseReadinessEvaluator().evaluate(
        release_manifest_sha256=RELEASE,
        evidence_entries=[_entry("LD-01", [("delivery", key)])],
        trust_root_inventory_bytes=payload,
        trust_root_authority_public_key=governance_public_key,
        expected_trust_root_inventory_file_sha256=pinned_sha256,
    )
    assert report["tasks"]["LD-01"]["passed"] is True
    assert report["trust_roots_authenticated"] is True

    with pytest.raises(GlyphChainReleaseReadinessError, match="authority_key_required"):
        GlyphChainReleaseReadinessEvaluator().evaluate(
            release_manifest_sha256=RELEASE,
            evidence_entries=[_entry("LD-01", [("delivery", key)])],
            trust_root_inventory_bytes=payload,
            expected_trust_root_inventory_file_sha256=pinned_sha256,
        )
    with pytest.raises(GlyphChainReleaseReadinessError, match="pin_invalid"):
        GlyphChainReleaseReadinessEvaluator().evaluate(
            release_manifest_sha256=RELEASE,
            evidence_entries=[_entry("LD-01", [("delivery", key)])],
            trust_root_inventory_bytes=payload,
            trust_root_authority_public_key=governance_public_key,
            expected_trust_root_inventory_file_sha256="00" * 32,
        )


def test_wrong_release_signature_role_and_non_independent_root_fail_closed():
    key, root = _key_root("delivery_operator", independent=False)
    body = _body("TR-02", release="ef" * 32)
    entry = {
        "task_id": "TR-02", "body": body,
        "attestations": [sign_evidence(body, signer_id="operator", private_key=key)],
    }
    report = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE, evidence_entries=[entry],
        trust_roots={"operator": root},
        trust_roots_authenticated=True,
    )
    errors = report["tasks"]["TR-02"]["errors"]
    assert "evidence_release_binding_invalid" in errors
    assert any(value.startswith("required_roles_missing") for value in errors)
    assert "independent_attestation_required" in errors
    entry["body"]["release_manifest_sha256"] = RELEASE
    second = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE, evidence_entries=[entry],
        trust_roots={"operator": root},
        trust_roots_authenticated=True,
    )
    assert any(value.startswith("evidence_signature_invalid") for value in second["tasks"]["TR-02"]["errors"])


def test_multi_role_task_requires_distinct_signers_and_an_independent_signer():
    key = Ed25519PrivateKey.generate()
    root = {
        "public_key_base64": base64.b64encode(key.public_key().public_bytes_raw()).decode("ascii"),
        "roles": ["delivery_operator", "security_reviewer"], "independent": True,
    }
    report = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE,
        evidence_entries=[_entry("LD-05", [("both", key)])], trust_roots={"both": root},
        trust_roots_authenticated=True,
    )
    assert "separation_of_duties_not_met" in report["tasks"]["LD-05"]["errors"]


def test_role_assignment_is_not_greedy_when_one_signer_has_multiple_roles():
    broad_key = Ed25519PrivateKey.generate()
    reviewer_key = Ed25519PrivateKey.generate()
    roots = {
        "broad": {
            "public_key_base64": base64.b64encode(broad_key.public_key().public_bytes_raw()).decode("ascii"),
            "roles": ["delivery_operator", "security_reviewer"],
            "independent": False,
        },
        "reviewer": {
            "public_key_base64": base64.b64encode(reviewer_key.public_key().public_bytes_raw()).decode("ascii"),
            "roles": ["security_reviewer"],
            "independent": True,
        },
    }
    report = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE,
        evidence_entries=[_entry("LD-05", [("broad", broad_key), ("reviewer", reviewer_key)])],
        trust_roots=roots,
        trust_roots_authenticated=True,
    )
    assert report["tasks"]["LD-05"]["passed"] is True
    assert report["tasks"]["LD-05"]["verified_role_signers"] == {
        "delivery_operator": "broad",
        "security_reviewer": "reviewer",
    }


def test_string_false_independence_and_invalid_or_future_observation_time_fail_closed():
    key, root = _key_root("independent_trust_publisher")
    root["independent"] = "false"
    body = _body("TR-02")
    body["observed_at"] = "not-a-time"
    entry = {
        "task_id": "TR-02",
        "body": body,
        "attestations": [sign_evidence(body, signer_id="publisher", private_key=key)],
    }
    invalid = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE,
        evidence_entries=[entry],
        trust_roots={"publisher": root},
        trust_roots_authenticated=True,
        generated_at="2026-09-27T14:00:00Z",
    )
    errors = invalid["tasks"]["TR-02"]["errors"]
    assert "release_evidence_time_invalid" in errors
    assert "independent_attestation_required" in errors
    assert "trust_root_inventory_invalid" in errors
    assert "trust_root_independence_invalid:publisher" in invalid["trust_root_inventory_errors"]

    root["independent"] = True
    body["observed_at"] = "2026-09-27T14:00:01Z"
    entry["attestations"] = [sign_evidence(body, signer_id="publisher", private_key=key)]
    future = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE,
        evidence_entries=[entry],
        trust_roots={"publisher": root},
        trust_roots_authenticated=True,
        generated_at="2026-09-27T14:00:00Z",
    )
    assert "evidence_observed_at_in_future" in future["tasks"]["TR-02"]["errors"]


def test_report_binds_exact_evidence_and_trust_root_inventories():
    key, root = _key_root("delivery_operator")
    entry = _entry("LD-01", [("delivery", key)])
    report = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE,
        evidence_entries=[entry],
        trust_roots={"delivery": root},
        trust_roots_authenticated=True,
        generated_at="2026-09-27T14:00:00Z",
    )
    assert len(report["evidence_inventory_sha256"]) == 64
    assert len(report["trust_roots_sha256"]) == 64
    task = report["tasks"]["LD-01"]
    assert len(task["evidence_body_sha256"]) == 64
    assert len(task["artifact_manifest_sha256"]) == 64
    assert task["attestation_signer_ids"] == ["delivery"]
    changed = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE,
        evidence_entries=[{**entry, "unused": True}],
        trust_roots={"delivery": root},
        trust_roots_authenticated=True,
        generated_at="2026-09-27T14:00:00Z",
    )
    assert changed["evidence_inventory_sha256"] != report["evidence_inventory_sha256"]


def test_duplicate_public_key_cannot_impersonate_two_separate_authorities():
    key = Ed25519PrivateKey.generate()
    encoded = base64.b64encode(key.public_key().public_bytes_raw()).decode("ascii")
    roots = {
        "delivery": {
            "public_key_base64": encoded,
            "roles": ["delivery_operator"],
            "independent": False,
        },
        "reviewer": {
            "public_key_base64": encoded,
            "roles": ["security_reviewer"],
            "independent": True,
        },
    }
    report = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE,
        evidence_entries=[_entry("LD-05", [("delivery", key), ("reviewer", key)])],
        trust_roots=roots,
        trust_roots_authenticated=True,
    )
    assert report["tasks"]["LD-05"]["passed"] is False
    assert "trust_root_inventory_invalid" in report["tasks"]["LD-05"]["errors"]
    assert any(
        error.startswith("trust_root_public_key_duplicate:")
        for error in report["trust_root_inventory_errors"]
    )


def test_complete_independently_signed_inventory_can_satisfy_but_not_manufacture_all_gates():
    roles = sorted({role for task in TASKS.values() for role in task["required_roles"]})
    keys = {}
    roots = {}
    for role in roles:
        key, root = _key_root(role, independent=True)
        signer_id = f"authority-{role}"
        keys[role] = (signer_id, key)
        roots[signer_id] = root
    entries = []
    for task_id, task in TASKS.items():
        if task_id != "REL-10":
            entries.append(_entry(task_id, [keys[role] for role in task["required_roles"]]))
    preauthorization = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE, evidence_entries=entries, trust_roots=roots,
        trust_roots_authenticated=True,
        trust_root_inventory_file_sha256="bb" * 32,
        trust_root_authority_key_id="ed25519:sha256:" + "cc" * 32,
    )
    assert preauthorization["result"] == "AWAITING_FINAL_RELEASE_AUTHORIZATION"
    assert preauthorization["preauthorization_ready"] is True
    assert preauthorization["passed_count"] == 33
    assert preauthorization["unmet_task_ids"] == ["REL-10"]
    preauthorization_bytes = (
        json.dumps(preauthorization, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    preauthorization_file_sha256 = hashlib.sha256(preauthorization_bytes).hexdigest()
    final_body = _body("REL-10")
    for artifact in final_body["artifacts"]:
        if artifact["kind"] == "preauthorization_readiness_report":
            artifact["sha256"] = preauthorization_file_sha256
    entries.append({
        "task_id": "REL-10",
        "body": final_body,
        "attestations": [
            sign_evidence(final_body, signer_id=keys[role][0], private_key=keys[role][1])
            for role in TASKS["REL-10"]["required_roles"]
        ],
    })
    report = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE,
        evidence_entries=entries,
        trust_roots=roots,
        trust_roots_authenticated=True,
        trust_root_inventory_file_sha256="bb" * 32,
        trust_root_authority_key_id="ed25519:sha256:" + "cc" * 32,
        preauthorization_report_bytes=preauthorization_bytes,
    )
    assert report["result"] == "ALL_RELEASE_GATES_EVIDENCED"
    assert report["passed_count"] == report["task_count"] == 34
    assert report["production_release_authorized"] is True
    assert report["preauthorization_ready"] is False
    assert report["preauthorization_report_sha256"] == preauthorization_file_sha256
    assert report["preauthorization_report_validated"] is True
    assert report["preauthorization_report_errors"] == []

    wrong_body = _body("REL-10")
    wrong_entry = {
        "task_id": "REL-10",
        "body": wrong_body,
        "attestations": [
            sign_evidence(wrong_body, signer_id=keys[role][0], private_key=keys[role][1])
            for role in TASKS["REL-10"]["required_roles"]
        ],
    }
    wrong = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE,
        evidence_entries=[*entries[:-1], wrong_entry],
        trust_roots=roots,
        trust_roots_authenticated=True,
        trust_root_inventory_file_sha256="bb" * 32,
        trust_root_authority_key_id="ed25519:sha256:" + "cc" * 32,
        preauthorization_report_bytes=preauthorization_bytes,
    )
    assert "preauthorization_report_binding_invalid" in wrong["tasks"]["REL-10"]["errors"]

    changed_entries = json.loads(json.dumps(entries))
    changed_entries[0]["unreviewed_top_level_change"] = True
    changed = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE,
        evidence_entries=changed_entries,
        trust_roots=roots,
        trust_roots_authenticated=True,
        trust_root_inventory_file_sha256="bb" * 32,
        trust_root_authority_key_id="ed25519:sha256:" + "cc" * 32,
        preauthorization_report_bytes=preauthorization_bytes,
    )
    assert changed["preauthorization_report_errors"] == [
        "preauthorization_report_evidence_inventory_binding_invalid"
    ]
    assert "preauthorization_report_not_validated" in changed["tasks"]["REL-10"]["errors"]


def test_final_release_authorization_requires_exact_preauthorization_report_binding():
    roots = {}
    keys = {}
    for role in TASKS["REL-10"]["required_roles"]:
        key, root = _key_root(role, independent=True)
        signer_id = f"authority-{role}"
        keys[role] = (signer_id, key)
        roots[signer_id] = root
    body = _body("REL-10")
    entry = {
        "task_id": "REL-10",
        "body": body,
        "attestations": [
            sign_evidence(body, signer_id=keys[role][0], private_key=keys[role][1])
            for role in TASKS["REL-10"]["required_roles"]
        ],
    }
    missing = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE,
        evidence_entries=[entry],
        trust_roots=roots,
        trust_roots_authenticated=True,
    )
    assert "preauthorization_report_required" in missing["tasks"]["REL-10"]["errors"]

    malformed = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE,
        evidence_entries=[entry],
        trust_roots=roots,
        trust_roots_authenticated=True,
        preauthorization_report_bytes=b"{}",
    )
    assert "preauthorization_report_not_validated" in malformed["tasks"]["REL-10"]["errors"]
    assert malformed["preauthorization_report_errors"] == [
        "preauthorization_report_digest_invalid"
    ]


def test_unknown_duplicate_malformed_artifact_and_report_tamper_block_release(tmp_path):
    key, root = _key_root("delivery_operator")
    valid = _entry("LD-01", [("delivery", key)])
    malformed = json.loads(json.dumps(valid))
    malformed["body"]["artifacts"][0]["sha256"] = "short"
    report = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE,
        evidence_entries=[valid, malformed, {"task_id": "UNKNOWN", "body": {}, "attestations": []}],
        trust_roots={"delivery": root},
        trust_roots_authenticated=True,
    )
    assert report["production_release_authorized"] is False
    assert report["duplicate_task_ids"] == ["LD-01"]
    assert report["unknown_task_ids"] == ["UNKNOWN"]
    output = tmp_path / "readiness.json"
    GlyphChainReleaseReadinessEvaluator.write_report(output, report)
    assert output.stat().st_mode & 0o777 == 0o600
    loaded = json.loads(output.read_text(encoding="utf-8"))
    loaded["unmet_count"] -= 1
    assert GlyphChainReleaseReadinessEvaluator.verify_report(loaded) is False
    with pytest.raises(FileExistsError):
        GlyphChainReleaseReadinessEvaluator.write_report(output, report)


def test_task_specific_artifact_contract_rejects_wrong_kind_missing_id_and_duplicate_id():
    key, root = _key_root("delivery_operator")
    body = _body("LD-01")
    body["artifacts"] = [{
        "artifact_id": "ld-01:wrong",
        "kind": "pilot_metrics_report",
        "sha256": "aa" * 32,
    }]
    wrong_kind = {
        "task_id": "LD-01",
        "body": body,
        "attestations": [sign_evidence(body, signer_id="delivery", private_key=key)],
    }
    report = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE,
        evidence_entries=[wrong_kind],
        trust_roots={"delivery": root},
        trust_roots_authenticated=True,
    )
    assert any(
        error.startswith("required_artifacts_missing:")
        for error in report["tasks"]["LD-01"]["errors"]
    )

    body = _body("LD-01")
    body["artifacts"][0].pop("artifact_id")
    missing_id = {
        "task_id": "LD-01",
        "body": body,
        "attestations": [sign_evidence(body, signer_id="delivery", private_key=key)],
    }
    report = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE,
        evidence_entries=[missing_id],
        trust_roots={"delivery": root},
        trust_roots_authenticated=True,
    )
    assert "evidence_artifact_invalid" in report["tasks"]["LD-01"]["errors"]

    body = _body("LD-01")
    body["artifacts"][1]["artifact_id"] = body["artifacts"][0]["artifact_id"]
    duplicate_id = {
        "task_id": "LD-01",
        "body": body,
        "attestations": [sign_evidence(body, signer_id="delivery", private_key=key)],
    }
    report = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=RELEASE,
        evidence_entries=[duplicate_id],
        trust_roots={"delivery": root},
        trust_roots_authenticated=True,
    )
    assert "evidence_artifact_id_duplicate" in report["tasks"]["LD-01"]["errors"]


def test_offline_evidence_creator_and_separate_authority_countersigning(tmp_path):
    release = tmp_path / "release.json"
    artifact = tmp_path / "delivery-report.json"
    delivery_key_path = tmp_path / "delivery.pem"
    reviewer_key_path = tmp_path / "reviewer.pem"
    first_entry = tmp_path / "first.json"
    countersigned_entry = tmp_path / "countersigned.json"
    inventory_path = tmp_path / "inventory.json"
    roots_path = tmp_path / "roots.json"
    delivery_public_path = tmp_path / "delivery-public.pem"
    reviewer_public_path = tmp_path / "reviewer-public.pem"
    governance_key_path = tmp_path / "governance.pem"
    governance_public_path = tmp_path / "governance-public.pem"
    readiness_path = tmp_path / "readiness.json"
    release.write_text('{"release":"candidate"}\n', encoding="utf-8")
    artifact.write_text('{"result":"PASS"}\n', encoding="utf-8")
    delivery_key, delivery_root = _key_root("delivery_operator")
    reviewer_key, reviewer_root = _key_root("security_reviewer", independent=True)
    delivery_key_path.write_bytes(delivery_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    reviewer_key_path.write_bytes(reviewer_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(b"review-password"),
    ))
    delivery_key_path.chmod(0o600)
    reviewer_key_path.chmod(0o600)
    delivery_public_path.write_bytes(delivery_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ))
    reviewer_public_path.write_bytes(reviewer_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ))
    governance_key = Ed25519PrivateKey.generate()
    governance_key_path.write_bytes(governance_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(b"governance-password"),
    ))
    governance_key_path.chmod(0o600)

    create = subprocess.run(
        [
            sys.executable,
            "backend/scripts/create_glyphchain_release_evidence.py",
            "create",
            "--task-id", "LD-05",
            "--release-manifest", str(release),
            "--artifact", f"production_delivery_qualification_report=delivery-qualification-1={artifact}",
            "--statement", "Production delivery qualification reviewed",
            "--observed-at", "2026-09-26T14:00:00Z",
            "--signer-id", "delivery-operator",
            "--private-key", str(delivery_key_path),
            "--output", str(first_entry),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert create.returncode == 0, create.stderr
    assert first_entry.stat().st_mode & 0o777 == 0o600
    attest = subprocess.run(
        [
            sys.executable,
            "backend/scripts/create_glyphchain_release_evidence.py",
            "attest",
            "--entry", str(first_entry),
            "--signer-id", "security-reviewer",
            "--private-key", str(reviewer_key_path),
            "--key-password-environment", "TESSARIS_TEST_REVIEW_KEY_PASSWORD",
            "--output", str(countersigned_entry),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "TESSARIS_TEST_REVIEW_KEY_PASSWORD": "review-password"},
    )
    assert attest.returncode == 0, attest.stderr
    entry = json.loads(countersigned_entry.read_text(encoding="utf-8"))
    report = GlyphChainReleaseReadinessEvaluator()._evaluate_verified(
        release_manifest_sha256=hashlib.sha256(release.read_bytes()).hexdigest(),
        evidence_entries=[entry],
        trust_roots={
            "delivery-operator": delivery_root,
            "security-reviewer": reviewer_root,
        },
        trust_roots_authenticated=True,
    )
    assert report["tasks"]["LD-05"]["passed"] is True
    assert report["tasks"]["LD-05"]["artifact_count"] == 1

    inventory = subprocess.run(
        [
            sys.executable,
            "backend/scripts/create_glyphchain_release_evidence.py",
            "inventory",
            "--entry", str(countersigned_entry),
            "--output", str(inventory_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert inventory.returncode == 0, inventory.stderr
    trust_roots = subprocess.run(
        [
            sys.executable,
            "backend/scripts/create_glyphchain_release_trust_roots.py",
            "--root", f"delivery-operator={delivery_public_path}",
            "--root", f"security-reviewer={reviewer_public_path}",
            "--role", "delivery-operator=delivery_operator",
            "--role", "security-reviewer=security_reviewer",
            "--independent", "security-reviewer",
            "--authority-id", "release-governance",
            "--governance-private-key", str(governance_key_path),
            "--key-password-environment", "TESSARIS_TEST_GOVERNANCE_KEY_PASSWORD",
            "--authority-public-key-output", str(governance_public_path),
            "--output", str(roots_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "TESSARIS_TEST_GOVERNANCE_KEY_PASSWORD": "governance-password"},
    )
    assert trust_roots.returncode == 0, trust_roots.stderr
    roots_digest = hashlib.sha256(roots_path.read_bytes()).hexdigest()
    unpinned_readiness_path = tmp_path / "unpinned-readiness.json"
    unpinned = subprocess.run(
        [
            sys.executable,
            "backend/scripts/evaluate_glyphchain_legal_release_readiness.py",
            "--release-manifest", str(release),
            "--evidence-inventory", str(inventory_path),
            "--trust-roots", str(roots_path),
            "--trust-roots-authority-public-key", str(governance_public_path),
            "--output", str(unpinned_readiness_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert unpinned.returncode != 0
    assert "independently supplied pin" in unpinned.stderr
    assert not unpinned_readiness_path.exists()
    evaluated = subprocess.run(
        [
            sys.executable,
            "backend/scripts/evaluate_glyphchain_legal_release_readiness.py",
            "--release-manifest", str(release),
            "--evidence-inventory", str(inventory_path),
            "--trust-roots", str(roots_path),
            "--trust-roots-authority-public-key", str(governance_public_path),
            "--expected-trust-roots-sha256", roots_digest,
            "--output", str(readiness_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert evaluated.returncode == 2
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    assert readiness["tasks"]["LD-05"]["passed"] is True
    assert readiness["passed_count"] == 1 and readiness["unmet_count"] == 33

    tampered_roots_path = tmp_path / "tampered-roots.json"
    tampered_readiness_path = tmp_path / "tampered-readiness.json"
    tampered_roots = json.loads(roots_path.read_text(encoding="utf-8"))
    tampered_roots["trust_roots"]["security-reviewer"]["independent"] = False
    tampered_roots_path.write_text(json.dumps(tampered_roots), encoding="utf-8")
    tampered_roots_digest = hashlib.sha256(tampered_roots_path.read_bytes()).hexdigest()
    rejected = subprocess.run(
        [
            sys.executable,
            "backend/scripts/evaluate_glyphchain_legal_release_readiness.py",
            "--release-manifest", str(release),
            "--evidence-inventory", str(inventory_path),
            "--trust-roots", str(tampered_roots_path),
            "--trust-roots-authority-public-key", str(governance_public_path),
            "--expected-trust-roots-sha256", tampered_roots_digest,
            "--output", str(tampered_readiness_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert rejected.returncode != 0
    assert "authority signature is invalid" in rejected.stderr
    assert not tampered_readiness_path.exists()


def test_offline_evidence_creator_refuses_symlink_artifact(tmp_path):
    release = tmp_path / "release.json"
    artifact_target = tmp_path / "report.json"
    artifact_link = tmp_path / "report-link.json"
    key_path = tmp_path / "key.pem"
    output = tmp_path / "entry.json"
    release.write_text("{}\n", encoding="utf-8")
    artifact_target.write_text("{}\n", encoding="utf-8")
    artifact_link.symlink_to(artifact_target)
    key = Ed25519PrivateKey.generate()
    key_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    result = subprocess.run(
        [
            sys.executable,
            "backend/scripts/create_glyphchain_release_evidence.py",
            "create",
            "--task-id", "LD-05",
            "--release-manifest", str(release),
            "--artifact", f"production_delivery_qualification_report=delivery-report={artifact_link}",
            "--statement", "Reviewed",
            "--observed-at", "2026-09-26T14:00:00Z",
            "--signer-id", "delivery-operator",
            "--private-key", str(key_path),
            "--output", str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "Refusing symbolic-link evidence artifact" in result.stderr
    assert not output.exists()
