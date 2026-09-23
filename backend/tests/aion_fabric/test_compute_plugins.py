from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from backend.modules.aion_business.contracts.intelligence import IntelligenceRequest
from backend.modules.aion_business.runtime.compute_plugins import (
    ComputePlugin,
    ComputePluginRegistry,
    ComputeBudget,
    ComputeRuntimeController,
    accelerator_profiles,
    deployment_recipe,
    migration_contract,
    provider_adapter_profiles,
    qualify_operating_modes,
    validate_endpoint,
)


class Endpoint(BaseHTTPRequestHandler):
    requests = []

    def do_GET(self):
        body = json.dumps({"data": [{"id": "test-model"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(length))
        type(self).requests.append(
            {
                "path": self.path,
                "payload": payload,
                "authorization": self.headers.get("Authorization"),
            }
        )
        if self.path == "/api/generate":
            value = {"response": json.dumps({"answer": "local"})}
        elif ":generateContent" in self.path:
            value = {"candidates": [{"content": {"parts": [{"text": json.dumps({"answer": "gemini"})}]}}]}
        elif self.path == "/v1/messages":
            value = {"content": [{"text": json.dumps({"answer": "anthropic"})}]}
        else:
            value = {
                "choices": [
                    {"message": {"content": json.dumps({"answer": "private"})}}
                ]
            }
        body = json.dumps(value).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


@pytest.fixture
def endpoint():
    Endpoint.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Endpoint)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        worker.join(timeout=2)


def request(**input_values):
    return IntelligenceRequest(
        request_id="compute-1",
        brain_id="brain-1",
        task_class="analysis",
        input=input_values or {"question": "analyse this"},
        required_capabilities=["analyse"],
        output_schema={"required": ["answer"]},
    )


def test_endpoints_are_fail_closed_by_location_and_never_embed_credentials():
    assert validate_endpoint(
        "http://127.0.0.1:11434", location="local"
    ).endswith("11434")
    assert (
        validate_endpoint(
            "https://private.example.com", location="customer_cloud"
        )
        == "https://private.example.com"
    )
    with pytest.raises(PermissionError, match="loopback"):
        validate_endpoint("http://192.168.1.5:11434", location="local")
    with pytest.raises(PermissionError, match="requires_https"):
        validate_endpoint("http://private.example.com", location="customer_cloud")
    with pytest.raises(ValueError, match="credentials"):
        validate_endpoint("https://user:secret@example.com", location="customer_cloud")
    with pytest.raises(ValueError, match="secret_value"):
        ComputePlugin(
            adapter_id="bad",
            provider="x",
            model="x",
            engine="openai_compatible",
            location="external_api",
            endpoint="https://example.com",
            destination="x",
            secret_reference="sk-secret",
        )


def test_local_ollama_adapter_uses_portable_contract(endpoint):
    plugin = ComputePlugin(
        adapter_id="ollama",
        provider="local",
        model="gemma3:1b",
        engine="ollama",
        location="local",
        endpoint=endpoint,
    )
    registry = ComputePluginRegistry()
    registry.register(plugin)
    manifest, caller = registry.adapter("ollama")
    result = caller(request())
    assert manifest.location == "local"
    assert result["output"] == {"answer": "local"}
    assert result["usage"]["cost"] == 0
    assert Endpoint.requests[-1]["path"] == "/api/generate"
    assert registry.health("ollama")["healthy"] is True


def test_private_openai_compatible_endpoint_resolves_secret_only_at_call_time(endpoint):
    plugin = ComputePlugin(
        adapter_id="private",
        provider="customer",
        model="private-model",
        engine="openai_compatible",
        location="local",
        endpoint=endpoint,
        secret_reference="vault://compute/private",
    )
    registry = ComputePluginRegistry(
        secret_resolver=lambda ref: (
            "resolved-at-call-time" if ref == "vault://compute/private" else ""
        )
    )
    public = registry.register(plugin)
    result = registry.invoke(plugin, request())
    assert result["output"] == {"answer": "private"}
    assert Endpoint.requests[-1]["authorization"] == "Bearer resolved-at-call-time"
    assert "resolved-at-call-time" not in json.dumps(public)


def test_llama_cpp_and_optional_provider_adapters_use_one_governed_contract(endpoint):
    secrets = {
        "vault://gemini": "gemini-secret",
        "vault://anthropic": "anthropic-secret",
    }
    registry = ComputePluginRegistry(secret_resolver=lambda ref: secrets.get(ref, ""))
    plugins = [
        ComputePlugin(adapter_id="llama", provider="local", model="local", engine="llama_cpp", location="local", endpoint=endpoint),
        ComputePlugin(adapter_id="gemini", provider="gemini", model="gemini-test", engine="gemini", location="local", endpoint=endpoint, secret_reference="vault://gemini"),
        ComputePlugin(adapter_id="anthropic", provider="anthropic", model="claude-test", engine="anthropic", location="local", endpoint=endpoint, secret_reference="vault://anthropic"),
    ]
    for plugin in plugins:
        registry.register(plugin)
    assert registry.invoke(plugins[0], request())["output"] == {"answer": "private"}
    assert registry.invoke(plugins[1], request())["output"] == {"answer": "gemini"}
    assert registry.invoke(plugins[2], request())["output"] == {"answer": "anthropic"}
    public = json.dumps([plugin.public_record() for plugin in plugins])
    assert "gemini-secret" not in public
    assert "anthropic-secret" not in public


def test_provider_profiles_are_replaceable_and_do_not_contain_endpoints_or_keys():
    profiles = provider_adapter_profiles()
    assert {
        "local_llama_cpp", "local_ollama", "private_openai_compatible", "customer_aws_vpc",
        "customer_google_cloud", "customer_azure", "nvidia_nim", "prem_compatible",
        "gemini_optional", "openai_optional", "anthropic_optional",
    } <= set(profiles)
    encoded = json.dumps(profiles)
    assert "api_key" not in encoded
    assert "https://" not in encoded


def test_plugins_are_immutable_and_do_not_contain_business_state(endpoint):
    first = ComputePlugin(
        adapter_id="compute",
        provider="local",
        model="one",
        engine="ollama",
        location="local",
        endpoint=endpoint,
    )
    registry = ComputePluginRegistry()
    record = registry.register(first)
    assert "business_map" not in json.dumps(record)
    changed = ComputePlugin(
        adapter_id="compute",
        provider="local",
        model="two",
        engine="ollama",
        location="local",
        endpoint=endpoint,
    )
    with pytest.raises(PermissionError, match="immutable"):
        registry.register(changed)


def test_nvidia_and_customer_cloud_recipe_is_customer_owned_and_portable():
    nim = ComputePlugin(
        adapter_id="nim",
        provider="nvidia",
        model="qualified-nim-model",
        engine="nvidia_nim",
        location="customer_cloud",
        endpoint="https://inference.customer.example",
        destination="customer-vpc",
        region="eu-south-2",
        residency="eu",
        accelerator="nvidia",
        memory_bytes=24_000_000_000,
        network_policy="private_only",
        secret_reference="vault://compute/nvidia",
        network_required=True,
        metadata={
            "image": "nvcr.io/customer-approved/nim@sha256:abc",
            "resources": {"cpu": "4", "memory": "24Gi", "nvidia.com/gpu": "1"},
        },
    )
    recipe = deployment_recipe(
        nim,
        customer_account="customer-aws-account",
        maximum_replicas=3,
        scale_to_zero=True,
    )
    assert recipe["ownership"]["managed_by_tessaris"] is False
    assert recipe["portable_protocol"] == "openai-compatible-v1"
    assert recipe["workload"]["replicas"] == 0
    assert recipe["workload"]["maximum_replicas"] == 3
    assert recipe["network"]["egress"] == "deny_by_default"
    assert "vault://compute/nvidia" in recipe["workload"]["secret_references"]
    public = nim.public_record()
    assert public["region"] == "eu-south-2"
    assert public["accelerator"] == "nvidia"
    assert public["memory_bytes"] == 24_000_000_000
    assert public["network_policy"] == "private_only"


def test_compute_policy_fields_are_validated():
    with pytest.raises(ValueError, match="network_policy_invalid"):
        ComputePlugin(
            adapter_id="bad-policy", provider="customer", model="m", engine="openai_compatible",
            location="customer_cloud", endpoint="https://compute.example", destination="vpc",
            region="eu", network_policy="open_internet",
        )
    with pytest.raises(ValueError, match="compute_memory_invalid"):
        ComputePlugin(
            adapter_id="bad-memory", provider="customer", model="m", engine="openai_compatible",
            location="customer_cloud", endpoint="https://compute.example", destination="vpc",
            region="eu", memory_bytes=-1,
        )


def test_confidential_compute_requires_fresh_replaceable_attestation():
    verifier_calls = []
    plugin = ComputePlugin(
        adapter_id="confidential",
        provider="customer-cloud",
        model="private-model",
        engine="openai_compatible",
        location="customer_cloud",
        endpoint="https://confidential.customer.example",
        destination="customer-vpc",
        residency="eu",
        confidential_compute=True,
        attestation_provider="replaceable-verifier",
        accepted_measurements=("sha256:approved",),
    )
    registry = ComputePluginRegistry(
        attestation_verifiers={
            "replaceable-verifier": lambda evidence: (
                verifier_calls.append(evidence) or evidence.get("signature") == "valid"
            )
        }
    )
    evidence = {
        "measurement": "sha256:approved",
        "nonce": "unique-request-nonce",
        "signature": "valid",
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
    }
    registry._verify_attestation(plugin, evidence)
    assert verifier_calls == [evidence]

    expired = dict(evidence)
    expired["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with pytest.raises(PermissionError, match="expired"):
        registry._verify_attestation(plugin, expired)
    wrong_measurement = dict(evidence)
    wrong_measurement["measurement"] = "sha256:unknown"
    with pytest.raises(PermissionError, match="measurement"):
        registry._verify_attestation(plugin, wrong_measurement)


def test_accelerator_profiles_and_three_operating_modes_are_explicit(endpoint):
    profiles = accelerator_profiles()
    assert {"cpu", "apple_silicon", "nvidia", "qualified_future"} <= set(profiles)
    assert profiles["apple_silicon"]["backends"] == ["metal"]
    local = ComputePlugin(
        adapter_id="local",
        provider="local",
        model="small",
        engine="ollama",
        location="local",
        endpoint=endpoint,
    )
    public = ComputePlugin(
        adapter_id="public",
        provider="public-evidence",
        model="retrieval-synthesizer",
        engine="openai_compatible",
        location="customer_cloud",
        endpoint="https://public.customer.example",
        destination="customer-vpc",
        residency="eu",
        network_required=True,
        metadata={"public_evidence": True},
    )
    premium = ComputePlugin(
        adapter_id="premium",
        provider="optional-provider",
        model="premium",
        engine="openai_compatible",
        location="external_api",
        endpoint="https://premium.example",
        destination="premium-provider",
        residency="eu",
        network_required=True,
        paid=True,
    )
    modes = qualify_operating_modes([local, public, premium])
    assert modes["air_gapped"] == {"useful": True, "routes": ["local"]}
    assert modes["internet_no_paid_ai"]["useful"] is True
    assert modes["premium_enabled"]["optional"] is True
    assert modes["core_intelligence_requires_paid_provider"] is False


def test_compute_migration_preserves_brain_identity_state_policy_and_interfaces():
    contract = migration_contract(
        brain_id="brain-customer-1",
        brain_state_hash="sha256:canonical-state",
        source_adapter="local-ollama",
        destination_adapter="customer-nim",
    )
    assert contract["brain_state_hash_before"] == contract["brain_state_hash_required_after"]
    assert contract["business_map_migration_required"] is False
    assert contract["policy_migration_required"] is False
    assert contract["application_interface_change_required"] is False
    assert contract["model_state_is_authoritative"] is False


def test_compute_runtime_enforces_spend_energy_and_reports_capacity(endpoint):
    paid = ComputePlugin(
        adapter_id="paid",
        provider="customer",
        model="private",
        engine="openai_compatible",
        location="local",
        endpoint=endpoint,
        estimated_cost=0.25,
        estimated_energy_wh=0.5,
    )
    registry = ComputePluginRegistry()
    registry.register(paid)
    controller = ComputeRuntimeController(registry)
    assert controller.invoke(
        "paid", request(), budget=ComputeBudget(maximum_spend=0.1, maximum_energy_wh=1)
    )["error_code"] == "compute_spend_budget_exceeded"
    assert controller.invoke(
        "paid", request(), budget=ComputeBudget(maximum_spend=1, maximum_energy_wh=0.1)
    )["error_code"] == "compute_energy_budget_exceeded"
    result = controller.invoke(
        "paid", request(), budget=ComputeBudget(maximum_spend=1, maximum_energy_wh=1)
    )
    assert result["ok"] is True
    status = controller.status("paid", capacity=4)
    assert status["capacity"] == 4
    assert status["requests"] == 1
    assert status["spend"] == 0.25
    assert status["energy_wh"] == 0.5
    assert status["customer_content_exposed"] is False


def test_compute_runtime_circuit_breaker_and_scale_to_zero_are_bounded(endpoint):
    broken = ComputePlugin(
        adapter_id="broken",
        provider="local",
        model="broken",
        engine="unsupported",
        location="local",
        endpoint=endpoint,
        estimated_energy_wh=0,
    )
    registry = ComputePluginRegistry()
    registry.register(broken)
    controller = ComputeRuntimeController(
        registry, failure_threshold=2, circuit_seconds=30, scale_to_zero_after_seconds=1
    )
    budget = ComputeBudget(maximum_spend=0, maximum_energy_wh=0)
    assert controller.invoke("broken", request(), budget=budget)["ok"] is False
    assert controller.invoke("broken", request(), budget=budget)["ok"] is False
    assert controller.status("broken")["circuit"] == "open"
    assert controller.invoke("broken", request(), budget=budget)["error_code"] == "compute_circuit_open"
    controller._state["broken"]["circuit_open_until"] = 0
    controller._state["broken"]["last_activity"] -= 2
    assert controller.status("broken")["scale_state"] == "scaled_to_zero"
