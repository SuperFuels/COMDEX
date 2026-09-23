from __future__ import annotations

import ipaddress
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from backend.modules.aion_business.contracts.intelligence import (
    IntelligenceAdapterManifest,
    IntelligenceRequest,
)
from backend.modules.aion_fabric.canonical import canonical_hash, utc_now_iso


SecretResolver = Callable[[str], str]
AttestationVerifier = Callable[[Dict[str, Any]], bool]


def _is_loopback(hostname: str | None) -> bool:
    if not hostname:
        return False
    if hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def validate_endpoint(endpoint: str, *, location: str) -> str:
    parsed = urlparse(str(endpoint).rstrip("/"))
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("compute_endpoint_invalid")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("compute_endpoint_must_not_contain_credentials_or_query")
    if location == "local":
        if not _is_loopback(parsed.hostname):
            raise PermissionError("local_compute_must_use_loopback")
    elif parsed.scheme != "https":
        raise PermissionError("remote_compute_requires_https")
    return str(endpoint).rstrip("/")


@dataclass(frozen=True)
class ComputePlugin:
    adapter_id: str
    provider: str
    model: str
    engine: str
    location: str
    endpoint: str
    destination: str = "local"
    region: str = "local"
    residency: str = "local"
    accelerator: str = "cpu"
    memory_bytes: int = 0
    network_policy: str = "deny_by_default"
    secret_reference: str = ""
    capabilities: tuple[str, ...] = ("analyse", "draft", "structure")
    estimated_quality: float = 0.7
    estimated_cost: float = 0.0
    estimated_latency_ms: int = 1000
    estimated_energy_wh: float = 0.2
    network_required: bool = False
    paid: bool = False
    confidential_compute: bool = False
    attestation_provider: str = ""
    accepted_measurements: tuple[str, ...] = ()
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_endpoint(self.endpoint, location=self.location)
        if self.location != "local" and not self.destination.strip():
            raise ValueError("remote_destination_required")
        if self.location != "local" and not self.region.strip():
            raise ValueError("remote_region_required")
        if self.memory_bytes < 0:
            raise ValueError("compute_memory_invalid")
        if self.network_policy not in {"offline", "private_only", "allowlisted_egress", "deny_by_default"}:
            raise ValueError("compute_network_policy_invalid")
        if self.secret_reference and any(token in self.secret_reference.lower() for token in ("bearer ", "sk-", "api_key=")):
            raise ValueError("secret_value_must_not_be_stored_in_plugin")
        if self.confidential_compute and (not self.attestation_provider or not self.accepted_measurements):
            raise ValueError("confidential_compute_attestation_policy_required")

    def manifest(self) -> IntelligenceAdapterManifest:
        return IntelligenceAdapterManifest(
            adapter_id=self.adapter_id,
            kind="model",
            location=self.location,
            provider=self.provider,
            model=self.model,
            capabilities=list(self.capabilities),
            destination=self.destination,
            residency=self.residency,
            estimated_quality=self.estimated_quality,
            estimated_cost=self.estimated_cost,
            estimated_latency_ms=self.estimated_latency_ms,
            estimated_energy_wh=self.estimated_energy_wh,
        )

    def public_record(self) -> Dict[str, Any]:
        value = {
            "adapter_id": self.adapter_id,
            "provider": self.provider,
            "model": self.model,
            "engine": self.engine,
            "location": self.location,
            "endpoint": self.endpoint,
            "destination": self.destination,
            "region": self.region,
            "residency": self.residency,
            "accelerator": self.accelerator,
            "memory_bytes": self.memory_bytes,
            "network_policy": self.network_policy,
            "secret_reference": self.secret_reference,
            "capabilities": list(self.capabilities),
            "network_required": self.network_required,
            "paid": self.paid,
            "confidential_compute": self.confidential_compute,
            "attestation_provider": self.attestation_provider,
            "accepted_measurements": list(self.accepted_measurements),
            "metadata": self.metadata,
        }
        value["plugin_hash"] = canonical_hash(value)
        return value


class ComputePluginRegistry:
    """Replaceable compute adapters; never an authority over AION state or actions."""

    def __init__(self, *, secret_resolver: SecretResolver | None = None, attestation_verifiers: Dict[str, AttestationVerifier] | None = None) -> None:
        self.secret_resolver = secret_resolver
        self.attestation_verifiers = dict(attestation_verifiers or {})
        self._plugins: Dict[str, ComputePlugin] = {}

    def register(self, plugin: ComputePlugin) -> Dict[str, Any]:
        existing = self._plugins.get(plugin.adapter_id)
        if existing and existing.public_record()["plugin_hash"] != plugin.public_record()["plugin_hash"]:
            raise PermissionError("immutable_compute_plugin_conflict")
        self._plugins[plugin.adapter_id] = plugin
        return plugin.public_record()

    def adapter(self, adapter_id: str):
        plugin = self._plugins[adapter_id]
        return plugin.manifest(), lambda request: self.invoke(plugin, request)

    def invoke(self, plugin: ComputePlugin, request: IntelligenceRequest) -> Dict[str, Any]:
        if plugin.confidential_compute:
            evidence = dict(request.input.get("_attestation") or {})
            self._verify_attestation(plugin, evidence)
        secret = ""
        if plugin.secret_reference:
            if not self.secret_resolver:
                return {"ok": False, "error_code": "secret_resolver_unavailable"}
            secret = self.secret_resolver(plugin.secret_reference)
            if not secret:
                return {"ok": False, "error_code": "compute_credential_unavailable"}
        if plugin.engine == "ollama":
            return self._invoke_ollama(plugin, request)
        if plugin.engine in {"openai_compatible", "nvidia_nim", "llama_cpp"}:
            return self._invoke_openai_compatible(plugin, request, secret)
        if plugin.engine == "gemini":
            return self._invoke_gemini(plugin, request, secret)
        if plugin.engine == "anthropic":
            return self._invoke_anthropic(plugin, request, secret)
        return {"ok": False, "error_code": "compute_engine_not_supported"}

    def health(self, adapter_id: str, *, timeout_seconds: float = 2.0) -> Dict[str, Any]:
        plugin = self._plugins[adapter_id]
        path = str(plugin.metadata.get("health_path") or ("/api/tags" if plugin.engine == "ollama" else "/v1/models"))
        began = time.monotonic()
        try:
            request = Request(plugin.endpoint + path, headers={"Accept": "application/json"})
            with urlopen(request, timeout=timeout_seconds) as response:
                status = int(response.status)
                response.read(32_768)
            return {"healthy": 200 <= status < 300, "status": status, "latency_ms": int((time.monotonic() - began) * 1000)}
        except Exception as exc:
            return {"healthy": False, "error": type(exc).__name__, "latency_ms": int((time.monotonic() - began) * 1000)}

    def _verify_attestation(self, plugin: ComputePlugin, evidence: Dict[str, Any]) -> None:
        verifier = self.attestation_verifiers.get(plugin.attestation_provider)
        if not verifier:
            raise PermissionError("attestation_verifier_unavailable")
        if evidence.get("measurement") not in plugin.accepted_measurements:
            raise PermissionError("attestation_measurement_not_allowed")
        expires_at = str(evidence.get("expires_at") or "")
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise PermissionError("attestation_expiry_invalid") from exc
        if expiry <= datetime.now(timezone.utc):
            raise PermissionError("attestation_expired")
        if not evidence.get("nonce") or verifier(evidence) is not True:
            raise PermissionError("attestation_invalid")

    @staticmethod
    def _invoke_ollama(plugin: ComputePlugin, request: IntelligenceRequest) -> Dict[str, Any]:
        payload = {
            "model": plugin.model,
            "prompt": json.dumps(request.input, ensure_ascii=False, sort_keys=True),
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
        raw = ComputePluginRegistry._post_json(plugin.endpoint + "/api/generate", payload, {})
        response = raw.get("response")
        try:
            output = json.loads(response) if isinstance(response, str) else dict(response or {})
        except (ValueError, TypeError):
            return {"ok": False, "error_code": "structured_output_invalid"}
        return {"ok": isinstance(output, dict), "output": output, "quality_score": plugin.estimated_quality, "usage": {"cost": 0, "energy_wh": plugin.estimated_energy_wh}}

    @staticmethod
    def _invoke_openai_compatible(plugin: ComputePlugin, request: IntelligenceRequest, secret: str) -> Dict[str, Any]:
        payload = {
            "model": plugin.model,
            "messages": [{"role": "user", "content": json.dumps(request.input, ensure_ascii=False, sort_keys=True)}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {secret}"} if secret else {}
        raw = ComputePluginRegistry._post_json(plugin.endpoint + "/v1/chat/completions", payload, headers)
        try:
            content = raw["choices"][0]["message"]["content"]
            output = json.loads(content) if isinstance(content, str) else dict(content)
        except (KeyError, IndexError, TypeError, ValueError):
            return {"ok": False, "error_code": "structured_output_invalid"}
        return {"ok": True, "output": output, "quality_score": plugin.estimated_quality, "usage": {"cost": plugin.estimated_cost, "energy_wh": plugin.estimated_energy_wh}}

    @staticmethod
    def _invoke_gemini(plugin: ComputePlugin, request: IntelligenceRequest, secret: str) -> Dict[str, Any]:
        if not secret:
            return {"ok": False, "error_code": "compute_credential_unavailable"}
        payload = {
            "contents": [{"role": "user", "parts": [{"text": json.dumps(request.input, ensure_ascii=False, sort_keys=True)}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        }
        model = plugin.model.replace("/", "")
        raw = ComputePluginRegistry._post_json(
            f"{plugin.endpoint}/v1beta/models/{model}:generateContent",
            payload,
            {"x-goog-api-key": secret},
        )
        try:
            content = raw["candidates"][0]["content"]["parts"][0]["text"]
            output = json.loads(content) if isinstance(content, str) else dict(content)
        except (KeyError, IndexError, TypeError, ValueError):
            return {"ok": False, "error_code": "structured_output_invalid"}
        return {"ok": True, "output": output, "quality_score": plugin.estimated_quality, "usage": {"cost": plugin.estimated_cost, "energy_wh": plugin.estimated_energy_wh}}

    @staticmethod
    def _invoke_anthropic(plugin: ComputePlugin, request: IntelligenceRequest, secret: str) -> Dict[str, Any]:
        if not secret:
            return {"ok": False, "error_code": "compute_credential_unavailable"}
        payload = {
            "model": plugin.model,
            "max_tokens": int(plugin.metadata.get("max_output_tokens") or 1024),
            "temperature": 0,
            "messages": [{"role": "user", "content": json.dumps(request.input, ensure_ascii=False, sort_keys=True)}],
        }
        raw = ComputePluginRegistry._post_json(
            plugin.endpoint + "/v1/messages",
            payload,
            {"x-api-key": secret, "anthropic-version": str(plugin.metadata.get("api_version") or "2023-06-01")},
        )
        try:
            content = raw["content"][0]["text"]
            output = json.loads(content) if isinstance(content, str) else dict(content)
        except (KeyError, IndexError, TypeError, ValueError):
            return {"ok": False, "error_code": "structured_output_invalid"}
        return {"ok": True, "output": output, "quality_score": plugin.estimated_quality, "usage": {"cost": plugin.estimated_cost, "energy_wh": plugin.estimated_energy_wh}}

    @staticmethod
    def _post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        request = Request(url, data=json.dumps(payload).encode("utf-8"), method="POST", headers={"Content-Type": "application/json", "Accept": "application/json", **headers})
        with urlopen(request, timeout=30) as response:
            if not 200 <= int(response.status) < 300:
                raise RuntimeError("compute_endpoint_rejected_request")
            raw = response.read(2_000_000)
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("compute_response_must_be_object")
        return value


@dataclass(frozen=True)
class ComputeBudget:
    maximum_spend: float = 0.0
    maximum_seconds: float = 60.0
    maximum_energy_wh: float = 1.0
    maximum_concurrency: int = 1

    def __post_init__(self) -> None:
        if self.maximum_spend < 0 or self.maximum_seconds <= 0 or self.maximum_energy_wh < 0:
            raise ValueError("compute_budget_invalid")
        if not 1 <= self.maximum_concurrency <= 128:
            raise ValueError("compute_concurrency_out_of_range")


class ComputeRuntimeController:
    """Budget, capacity and circuit-breaker control around replaceable compute plugins."""

    def __init__(
        self,
        registry: ComputePluginRegistry,
        *,
        failure_threshold: int = 3,
        circuit_seconds: float = 30.0,
        scale_to_zero_after_seconds: float = 300.0,
    ) -> None:
        if not 1 <= int(failure_threshold) <= 20:
            raise ValueError("failure_threshold_out_of_range")
        self.registry = registry
        self.failure_threshold = int(failure_threshold)
        self.circuit_seconds = max(1.0, float(circuit_seconds))
        self.scale_to_zero_after_seconds = max(1.0, float(scale_to_zero_after_seconds))
        self._state: Dict[str, Dict[str, Any]] = {}

    def invoke(self, adapter_id: str, request: IntelligenceRequest, *, budget: ComputeBudget) -> Dict[str, Any]:
        plugin = self.registry._plugins[adapter_id]
        state = self._adapter_state(adapter_id)
        now = time.monotonic()
        if now < float(state["circuit_open_until"]):
            return {"ok": False, "error_code": "compute_circuit_open", "retry_after_seconds": round(state["circuit_open_until"] - now, 3)}
        if int(state["in_flight"]) >= budget.maximum_concurrency:
            state["queue_depth"] = int(state["queue_depth"]) + 1
            return {"ok": False, "error_code": "compute_capacity_exhausted", "queue_depth": state["queue_depth"]}
        if float(state["spend"]) + float(plugin.estimated_cost) > budget.maximum_spend:
            return {"ok": False, "error_code": "compute_spend_budget_exceeded"}
        if float(state["energy_wh"]) + float(plugin.estimated_energy_wh) > budget.maximum_energy_wh:
            return {"ok": False, "error_code": "compute_energy_budget_exceeded"}

        state["in_flight"] += 1
        state["scale_state"] = "active"
        began = time.monotonic()
        try:
            result = self.registry.invoke(plugin, request)
        except Exception as exc:
            result = {"ok": False, "error_code": f"compute_invocation_failed:{type(exc).__name__}"}
        finally:
            elapsed = time.monotonic() - began
            state["in_flight"] = max(0, int(state["in_flight"]) - 1)
            state["queue_depth"] = max(0, int(state["queue_depth"]) - 1)
            state["last_activity"] = time.monotonic()

        if elapsed > budget.maximum_seconds:
            result = {"ok": False, "error_code": "compute_time_budget_exceeded", "elapsed_seconds": round(elapsed, 3)}
        usage = dict(result.get("usage") or {})
        state["requests"] += 1
        state["spend"] += max(0.0, float(usage.get("cost", plugin.estimated_cost) or 0))
        state["energy_wh"] += max(0.0, float(usage.get("energy_wh", plugin.estimated_energy_wh) or 0))
        if result.get("ok") is True:
            state["consecutive_failures"] = 0
            state["circuit_open_until"] = 0.0
        else:
            state["consecutive_failures"] += 1
            if state["consecutive_failures"] >= self.failure_threshold:
                state["circuit_open_until"] = time.monotonic() + self.circuit_seconds
        return result

    def status(self, adapter_id: str, *, capacity: int | None = None) -> Dict[str, Any]:
        state = self._adapter_state(adapter_id)
        now = time.monotonic()
        if int(state["in_flight"]) == 0 and now - float(state["last_activity"]) >= self.scale_to_zero_after_seconds:
            state["scale_state"] = "scaled_to_zero"
        return {
            "adapter_id": adapter_id,
            "capacity": max(0, int(capacity if capacity is not None else 1)),
            "in_flight": int(state["in_flight"]),
            "queue_depth": int(state["queue_depth"]),
            "requests": int(state["requests"]),
            "spend": round(float(state["spend"]), 8),
            "energy_wh": round(float(state["energy_wh"]), 8),
            "circuit": "open" if now < float(state["circuit_open_until"]) else "closed",
            "consecutive_failures": int(state["consecutive_failures"]),
            "scale_state": state["scale_state"],
            "customer_content_exposed": False,
        }

    def reset_accounting(self, adapter_id: str) -> Dict[str, Any]:
        state = self._adapter_state(adapter_id)
        state.update({"requests": 0, "spend": 0.0, "energy_wh": 0.0})
        return self.status(adapter_id)

    def _adapter_state(self, adapter_id: str) -> Dict[str, Any]:
        if adapter_id not in self.registry._plugins:
            raise KeyError("compute_adapter_not_registered")
        return self._state.setdefault(adapter_id, {
            "in_flight": 0,
            "queue_depth": 0,
            "requests": 0,
            "spend": 0.0,
            "energy_wh": 0.0,
            "consecutive_failures": 0,
            "circuit_open_until": 0.0,
            "last_activity": time.monotonic(),
            "scale_state": "idle",
        })


def accelerator_profiles() -> Dict[str, Dict[str, Any]]:
    return {
        "cpu": {"engines": ["llama.cpp", "ollama"], "device_classes": ["personal", "small_business"], "requires_gpu": False},
        "apple_silicon": {"engines": ["llama.cpp", "ollama"], "backends": ["metal"], "requires_gpu": False},
        "nvidia": {"engines": ["nvidia_nim", "openai_compatible", "llama_cpp", "ollama"], "backends": ["cuda"], "requires_gpu": True},
        "qualified_future": {"engines": [], "activation": "signed_profile_and_benchmark_required", "requires_gpu": None},
    }


def provider_adapter_profiles() -> Dict[str, Dict[str, Any]]:
    """Provider-neutral adapter families; endpoints and keys remain customer bindings."""
    return {
        "local_llama_cpp": {"engine": "llama_cpp", "protocol": "openai-compatible-v1", "location": "local", "credential": "optional_vault_reference"},
        "local_ollama": {"engine": "ollama", "protocol": "ollama-json-v1", "location": "local", "credential": "none"},
        "private_openai_compatible": {"engine": "openai_compatible", "protocol": "openai-compatible-v1", "location": "customer_cloud", "credential": "vault_reference"},
        "customer_aws_vpc": {"engine": "openai_compatible", "protocol": "openai-compatible-v1", "location": "customer_cloud", "ownership": "customer", "credential": "vault_reference"},
        "customer_google_cloud": {"engine": "openai_compatible", "protocol": "openai-compatible-v1", "location": "customer_cloud", "ownership": "customer", "credential": "vault_reference"},
        "customer_azure": {"engine": "openai_compatible", "protocol": "openai-compatible-v1", "location": "customer_cloud", "ownership": "customer", "credential": "vault_reference"},
        "nvidia_nim": {"engine": "nvidia_nim", "protocol": "openai-compatible-v1", "location": "customer_cloud", "credential": "vault_reference"},
        "prem_compatible": {"engine": "openai_compatible", "protocol": "openai-compatible-v1", "location": "customer_cloud", "credential": "vault_reference"},
        "gemini_optional": {"engine": "gemini", "protocol": "gemini-generate-content-v1beta", "location": "external_api", "credential": "vault_reference"},
        "openai_optional": {"engine": "openai_compatible", "protocol": "openai-compatible-v1", "location": "external_api", "credential": "vault_reference"},
        "anthropic_optional": {"engine": "anthropic", "protocol": "anthropic-messages-v1", "location": "external_api", "credential": "vault_reference"},
    }


def deployment_recipe(plugin: ComputePlugin, *, customer_account: str, namespace: str = "aion-compute", maximum_replicas: int = 2, scale_to_zero: bool = True) -> Dict[str, Any]:
    if plugin.location == "local":
        raise ValueError("cloud_recipe_requires_remote_plugin")
    if not customer_account.strip():
        raise ValueError("customer_account_required")
    if not 1 <= maximum_replicas <= 20:
        raise ValueError("maximum_replicas_out_of_range")
    image = str(plugin.metadata.get("image") or "")
    if not image:
        raise ValueError("container_image_required")
    recipe = {
        "schema_version": "aion.customer_compute_recipe.v1",
        "ownership": {"account": customer_account, "managed_by_tessaris": False},
        "provider": plugin.provider,
        "portable_protocol": "openai-compatible-v1",
        "namespace": namespace,
        "workload": {
            "image": image,
            "replicas": 0 if scale_to_zero else 1,
            "maximum_replicas": maximum_replicas,
            "resources": plugin.metadata.get("resources") or {"cpu": "2", "memory": "8Gi"},
            "secret_references": [plugin.secret_reference] if plugin.secret_reference else [],
            "read_only_root_filesystem": True,
            "run_as_non_root": True,
        },
        "network": {"ingress": "private_only", "egress": "deny_by_default", "tls_required": True},
        "observability": {"health": "/v1/models", "metrics": "/metrics", "logs_may_contain_prompts": False},
        "autoscaling": {"enabled": True, "minimum": 0 if scale_to_zero else 1, "maximum": maximum_replicas, "queue_metric": "aion_pending_requests"},
        "attestation": {"required": plugin.confidential_compute, "provider": plugin.attestation_provider},
        "created_at": utc_now_iso(),
    }
    recipe["recipe_hash"] = canonical_hash(recipe)
    return recipe


def qualify_operating_modes(plugins: Iterable[ComputePlugin]) -> Dict[str, Any]:
    values = list(plugins)
    air_gapped = [item.adapter_id for item in values if item.location == "local" and not item.network_required]
    no_paid = [item.adapter_id for item in values if not item.paid and (item.location == "local" or item.metadata.get("public_evidence") is True)]
    premium = [item.adapter_id for item in values if item.paid]
    return {
        "schema_version": "aion.compute_operating_modes.v1",
        "air_gapped": {"useful": bool(air_gapped), "routes": air_gapped},
        "internet_no_paid_ai": {"useful": bool(no_paid), "routes": no_paid},
        "premium_enabled": {"optional": True, "routes": premium},
        "core_intelligence_requires_paid_provider": False,
    }


def migration_contract(*, brain_id: str, brain_state_hash: str, source_adapter: str, destination_adapter: str) -> Dict[str, Any]:
    contract = {
        "schema_version": "aion.compute_migration.v1",
        "brain_id": brain_id,
        "brain_state_hash_before": brain_state_hash,
        "brain_state_hash_required_after": brain_state_hash,
        "source_adapter": source_adapter,
        "destination_adapter": destination_adapter,
        "model_state_is_authoritative": False,
        "business_map_migration_required": False,
        "policy_migration_required": False,
        "application_interface_change_required": False,
    }
    contract["contract_hash"] = canonical_hash(contract)
    return contract
