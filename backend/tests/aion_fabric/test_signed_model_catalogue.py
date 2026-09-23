from __future__ import annotations

import hashlib
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.signed_model_catalogue import (
    BENCHMARK_METRICS,
    SignedModelCatalogue,
)
from backend.modules.aion_fabric.identity import DeviceIdentity
from backend.modules.aion_fabric.canonical import canonical_bytes


def identity() -> DeviceIdentity:
    return DeviceIdentity(Ed25519PrivateKey.generate())


def manifest(issuer: DeviceIdentity, artifact, model_id="gemma-local", version="1"):
    raw = artifact.read_bytes()
    return SignedModelCatalogue.sign_manifest(
        {
            "model_id": model_id,
            "version": version,
            "provider": "local",
            "artifact": {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)},
            "licence": {
                "id": "Apache-2.0",
                "commercial_use_allowed": True,
                "redistribution_allowed": True,
                "source": "https://www.apache.org/licenses/LICENSE-2.0",
                "attribution_required": True,
            },
            "mirrors": ["https://models.example.invalid/gemma.gguf"],
            "compatibility": {
                "minimum_memory_bytes": 4_000_000_000,
                "minimum_storage_bytes": len(raw),
                "architectures": ["arm64", "x86_64"],
                "accelerators": ["cpu", "apple_silicon"],
                "engines": ["llama.cpp", "ollama"],
            },
            "execution": {
                "adapter_family": "llama_cpp",
                "endpoint_protocol": "local-process-v1",
            },
            "capabilities": {
                "modalities": ["text"],
                "context_tokens": 8192,
                "structured_output": True,
                "tools": False,
                "languages": ["en", "es"],
                "domains": ["general"],
            },
            "estimates": {
                "latency_ms": 80,
                "cost_per_million_input_tokens": 0,
                "energy_wh_per_request": 0.4,
            },
        },
        issuer,
    )


def scores(**overrides):
    values = {
        "task": 0.90,
        "domain": 0.88,
        "safety": 0.98,
        "tool_use": 0.91,
        "latency": 80,
        "cost": 0,
        "energy": 0.4,
    }
    values.update(overrides)
    return values


def hardware(**overrides):
    values = {
        "architecture": "arm64",
        "memory_bytes": 16_000_000_000,
        "storage_free_bytes": 100_000_000_000,
        "accelerator_class": "apple_silicon",
    }
    values.update(overrides)
    return values


def thresholds():
    return {
        "task": 0.80,
        "domain": 0.80,
        "safety": 0.95,
        "tool_use": 0.85,
        "latency": 100,
        "cost": 0.01,
        "energy": 0.5,
    }


def registered(tmp_path, model_id="gemma-local"):
    issuer = identity()
    artifact = tmp_path / f"{model_id}.gguf"
    artifact.write_bytes((model_id + "-weights").encode())
    catalogue = SignedModelCatalogue(tmp_path / "catalogue", trusted_issuers=[issuer.public_key_b64])
    signed = manifest(issuer, artifact, model_id=model_id)
    catalogue.register(signed)
    return catalogue, issuer, artifact, SignedModelCatalogue.model_ref(signed)


def qualify(catalogue, model_ref):
    catalogue.record_benchmark(
        model_ref,
        suite_id="public-v1",
        visibility="public",
        scores=scores(),
        provenance={"suite_hash": "sha256:test-suite"},
    )
    return catalogue.qualify(model_ref, hardware=hardware(), engine="llama.cpp", thresholds=thresholds())


def test_signed_manifest_is_verified_trusted_and_immutable(tmp_path):
    catalogue, issuer, artifact, model_ref = registered(tmp_path)
    assert catalogue.record(model_ref)["status"] == "experimental"

    tampered = manifest(issuer, artifact)
    tampered["provider"] = "tampered"
    with pytest.raises(ValueError, match="hash_mismatch"):
        catalogue.register(tampered)

    stranger = identity()
    with pytest.raises(PermissionError, match="issuer_not_trusted"):
        catalogue.register(manifest(stranger, artifact, model_id="stranger"))

    changed = manifest(issuer, artifact)
    changed["mirrors"] = ["https://different.example.invalid/model.gguf"]
    changed = SignedModelCatalogue.sign_manifest(changed, issuer)
    with pytest.raises(PermissionError, match="immutable_model_version_conflict"):
        catalogue.register(changed)


def test_model_lifecycle_states_are_signed_and_manual_qualification_is_forbidden(tmp_path):
    catalogue, issuer, _artifact, model_ref = registered(tmp_path)
    unavailable = catalogue.set_availability(
        model_ref, status="unavailable", reason="endpoint maintenance", identity=issuer
    )
    signed = {key: value for key, value in unavailable.items() if key != "signature"}
    assert DeviceIdentity.verify(issuer.public_key_b64, canonical_bytes(signed), unavailable["signature"])
    assert catalogue.record(model_ref)["status"] == "unavailable"
    assert catalogue.admin_catalogue()["groups"]["unavailable"][0]["model_ref"] == model_ref
    with pytest.raises(ValueError, match="transition_not_allowed"):
        catalogue.set_availability(model_ref, status="qualified", reason="manual", identity=issuer)
    with pytest.raises(PermissionError, match="issuer_mismatch"):
        catalogue.set_availability(model_ref, status="deprecated", reason="old", identity=identity())


def test_editor_preflight_exposes_compatibility_cost_latency_energy_and_no_secrets(tmp_path):
    catalogue, _issuer, _artifact, model_ref = registered(tmp_path)
    result = catalogue.preflight(model_ref, hardware=hardware(), engine="llama.cpp")
    assert result["selectable"] is True
    assert result["compatibility"]["compatible"] is True
    assert result["estimates"] == {
        "latency_ms": 80,
        "cost_per_million_input_tokens": 0,
        "energy_wh_per_request": 0.4,
    }
    assert result["credentials_exposed"] is False
    assert result["customer_content_exposed"] is False
    assert "secret" not in json.dumps(result).lower()


def test_manifest_requires_portable_execution_capabilities_licence_and_estimates(tmp_path):
    issuer = identity()
    artifact = tmp_path / "model.gguf"
    artifact.write_bytes(b"model")
    complete = manifest(issuer, artifact)
    catalogue = SignedModelCatalogue(tmp_path / "catalogue", trusted_issuers=[issuer.public_key_b64])
    for missing, error in (
        ("execution", "fields_missing:execution"),
        ("capabilities", "fields_missing:capabilities"),
        ("estimates", "fields_missing:estimates"),
    ):
        payload = {key: value for key, value in complete.items() if key not in {missing, "manifest_hash", "signature"}}
        signed = SignedModelCatalogue.sign_manifest(payload, issuer)
        with pytest.raises(ValueError, match=error):
            catalogue.register(signed)

    bad_adapter = {key: value for key, value in complete.items() if key not in {"manifest_hash", "signature"}}
    bad_adapter["execution"] = {"adapter_family": "locked_vendor_runtime"}
    with pytest.raises(ValueError, match="adapter_family_not_supported"):
        catalogue.register(SignedModelCatalogue.sign_manifest(bad_adapter, issuer))


def test_hardware_and_installation_checks_fail_closed(tmp_path):
    catalogue, _issuer, artifact, model_ref = registered(tmp_path)
    assert catalogue.installation_check(
        model_ref, hardware=hardware(), engine="llama.cpp", artifact_path=artifact
    )["installable"] is True

    incompatible = catalogue.installation_check(
        model_ref,
        hardware=hardware(memory_bytes=1, architecture="riscv"),
        engine="unknown",
        artifact_path=artifact,
    )
    assert incompatible["installable"] is False
    assert {"insufficient_memory", "architecture_not_supported", "inference_engine_not_supported"} <= set(incompatible["failures"])

    artifact.write_bytes(b"tampered")
    assert catalogue.verify_artifact(model_ref, artifact)["verified"] is False


def test_all_benchmark_dimensions_are_required_and_private_scores_stay_private(tmp_path):
    catalogue, _issuer, _artifact, model_ref = registered(tmp_path)
    incomplete = scores()
    incomplete.pop("energy")
    with pytest.raises(ValueError, match="benchmark_metrics_missing:energy"):
        catalogue.record_benchmark(model_ref, suite_id="bad", visibility="public", scores=incomplete, provenance={})

    public = catalogue.record_benchmark(
        model_ref, suite_id="public", visibility="public", scores=scores(), provenance={"source": "repeatable-suite"}
    )
    private = catalogue.record_benchmark(
        model_ref,
        suite_id="customer-outcomes",
        visibility="customer_private",
        scores=scores(task=0.99),
        provenance={"source": "customer-receipts"},
        customer_id="customer-1",
    )
    assert set(public["scores"]) == set(BENCHMARK_METRICS)
    assert private["customer_id"] == "customer-1"
    admin = catalogue.admin_catalogue()
    assert admin["customer_private_outcomes_exposed"] is False
    assert "customer-1" not in json.dumps(admin)
    assert catalogue.private_scores_path.stat().st_mode & 0o777 == 0o600


def test_qualification_blocks_inferior_model_and_qualifies_accepted_model(tmp_path):
    catalogue, _issuer, _artifact, model_ref = registered(tmp_path)
    catalogue.record_benchmark(model_ref, suite_id="bad", visibility="public", scores=scores(safety=0.2), provenance={})
    result = catalogue.qualify(model_ref, hardware=hardware(), engine="llama.cpp", thresholds=thresholds())
    assert result["qualified"] is False
    assert "safety_minimum_not_met" in result["failures"]
    assert catalogue.record(model_ref)["status"] == "blocked"

    catalogue.record_benchmark(model_ref, suite_id="good", visibility="public", scores=scores(), provenance={})
    assert catalogue.qualify(model_ref, hardware=hardware(), engine="llama.cpp", thresholds=thresholds())["qualified"] is True


def test_bounded_champion_challenger_promotes_only_better_candidate_and_rolls_back(tmp_path):
    issuer = identity()
    catalogue = SignedModelCatalogue(tmp_path / "catalogue", trusted_issuers=[issuer.public_key_b64])
    refs = []
    for name in ("champion", "challenger"):
        artifact = tmp_path / f"{name}.gguf"
        artifact.write_bytes(name.encode())
        signed = manifest(issuer, artifact, model_id=name)
        catalogue.register(signed)
        ref = SignedModelCatalogue.model_ref(signed)
        qualify(catalogue, ref)
        refs.append(ref)

    champion, challenger = refs
    with pytest.raises(ValueError, match="percentage_out_of_range"):
        catalogue.start_canary(task_class="analysis", champion=champion, challenger=challenger, percentage=50, maximum_requests=2, thresholds=thresholds())

    catalogue.start_canary(task_class="analysis", champion=champion, challenger=challenger, percentage=10, maximum_requests=2, thresholds=thresholds())
    catalogue.record_canary_sample("analysis", champion_scores=scores(task=0.85), challenger_scores=scores(task=0.92))
    route = catalogue.record_canary_sample("analysis", champion_scores=scores(task=0.86), challenger_scores=scores(task=0.93))
    assert route["canary"]["status"] == "promoted"
    assert route["champion"] == challenger
    assert catalogue.rollback("analysis", reason="operator_request")["champion"] == champion


def test_inferior_canary_is_rejected_and_drift_triggers_automatic_rollback(tmp_path):
    issuer = identity()
    catalogue = SignedModelCatalogue(tmp_path / "catalogue", trusted_issuers=[issuer.public_key_b64])
    refs = []
    for name in ("stable", "candidate"):
        artifact = tmp_path / f"{name}.gguf"
        artifact.write_bytes(name.encode())
        signed = manifest(issuer, artifact, model_id=name)
        catalogue.register(signed)
        ref = SignedModelCatalogue.model_ref(signed)
        qualify(catalogue, ref)
        refs.append(ref)
    stable, candidate = refs

    catalogue.start_canary(task_class="draft", champion=stable, challenger=candidate, percentage=5, maximum_requests=1, thresholds=thresholds())
    rejected = catalogue.record_canary_sample("draft", champion_scores=scores(), challenger_scores=scores(safety=0.5))
    assert rejected["canary"]["status"] == "rejected"
    assert rejected["champion"] == stable

    catalogue.start_canary(task_class="analysis", champion=stable, challenger=candidate, percentage=5, maximum_requests=1, thresholds=thresholds())
    promoted = catalogue.record_canary_sample("analysis", champion_scores=scores(task=0.85), challenger_scores=scores(task=0.95))
    assert promoted["champion"] == candidate
    report = catalogue.detect_drift(candidate, baseline=scores(), current=scores(task=0.1), tolerances={"task": 0.05})
    assert report["drift_detected"] is True
    assert catalogue.admin_catalogue()["routes"]["analysis"]["champion"] == stable
    assert catalogue.record(candidate)["status"] == "blocked"


def test_signed_revocation_blocks_model_and_licence_controls_mirroring(tmp_path):
    catalogue, issuer, _artifact, model_ref = registered(tmp_path)
    qualify(catalogue, model_ref)
    plan = catalogue.mirror_plan([{"active": True, "model_ref": model_ref}, {"active": False, "model_ref": "unused@1"}])
    assert [item["model_ref"] for item in plan["artifacts"]] == [model_ref]

    revocation = catalogue.revoke(model_ref, reason="upstream security notice", identity=issuer)
    signed = {key: value for key, value in revocation.items() if key != "signature"}
    assert DeviceIdentity.verify(issuer.public_key_b64, canonical_bytes(signed), revocation["signature"])
    assert catalogue.record(model_ref)["status"] == "blocked"
    assert catalogue.mirror_plan([{"active": True, "model_ref": model_ref}])["artifacts"] == []


def test_model_operations_do_not_create_or_mutate_business_state(tmp_path):
    business_root = tmp_path / "business"
    business_root.mkdir()
    marker = business_root / "canonical_state.json"
    marker.write_text('{"customers": 7}', encoding="utf-8")
    before = hashlib.sha256(marker.read_bytes()).hexdigest()

    catalogue, _issuer, _artifact, model_ref = registered(tmp_path)
    qualify(catalogue, model_ref)
    catalogue.admin_catalogue()

    assert hashlib.sha256(marker.read_bytes()).hexdigest() == before
    assert list(business_root.iterdir()) == [marker]
