from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso
from backend.modules.aion_fabric.identity import DeviceIdentity


BENCHMARK_METRICS = ("task", "domain", "safety", "tool_use", "latency", "cost", "energy")
MODEL_LIFECYCLE_STATES = ("experimental", "qualified", "blocked", "unavailable", "deprecated")


class SignedModelCatalogue:
    """Customer-owned model qualification, rollout and rollback authority."""

    def __init__(self, root: str | Path, *, trusted_issuers: Iterable[str]) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.catalogue_path = self.root / "model_catalogue.json"
        self.private_scores_path = self.root / "customer_private_outcomes.json"
        self.trusted_issuers = set(trusted_issuers)

    @staticmethod
    def model_ref(manifest: Dict[str, Any]) -> str:
        return f"{manifest.get('model_id')}@{manifest.get('version')}"

    @staticmethod
    def sign_manifest(payload: Dict[str, Any], identity: DeviceIdentity) -> Dict[str, Any]:
        clean = {key: value for key, value in payload.items() if key not in {"signature", "manifest_hash"}}
        clean.setdefault("schema_version", "aion.signed_model_manifest.v1")
        clean["issuer_public_key"] = identity.public_key_b64
        clean["manifest_hash"] = canonical_hash(clean)
        clean["signature"] = identity.sign(canonical_bytes(clean))
        return clean

    def register(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        self._validate_manifest(manifest)
        signed = {key: value for key, value in manifest.items() if key != "signature"}
        if manifest["issuer_public_key"] not in self.trusted_issuers:
            raise PermissionError("model_manifest_issuer_not_trusted")
        if canonical_hash({key: value for key, value in signed.items() if key != "manifest_hash"}) != manifest["manifest_hash"]:
            raise ValueError("model_manifest_hash_mismatch")
        if not DeviceIdentity.verify(manifest["issuer_public_key"], canonical_bytes(signed), manifest["signature"]):
            raise ValueError("model_manifest_signature_invalid")
        state = self._state()
        ref = self.model_ref(manifest)
        existing = dict((state.get("models") or {}).get(ref) or {})
        if existing and existing.get("manifest_hash") != manifest["manifest_hash"]:
            raise PermissionError("immutable_model_version_conflict")
        state.setdefault("models", {})[ref] = {
            "manifest": manifest,
            "manifest_hash": manifest["manifest_hash"],
            "status": existing.get("status") or "experimental",
            "qualification": existing.get("qualification") or {},
            "public_benchmarks": existing.get("public_benchmarks") or [],
            "registered_at": existing.get("registered_at") or utc_now_iso(),
        }
        self._write(self.catalogue_path, state)
        return self.record(ref)

    def revoke(self, model_ref: str, *, reason: str, identity: DeviceIdentity) -> Dict[str, Any]:
        if not str(reason).strip():
            raise ValueError("revocation_reason_required")
        state = self._state()
        record = self._require(state, model_ref)
        if identity.public_key_b64 != record["manifest"]["issuer_public_key"]:
            raise PermissionError("revocation_issuer_mismatch")
        revocation = {"model_ref": model_ref, "manifest_hash": record["manifest_hash"], "reason": str(reason), "revoked_at": utc_now_iso(), "issuer_public_key": identity.public_key_b64}
        revocation["signature"] = identity.sign(canonical_bytes(revocation))
        record.update({"status": "blocked", "revocation": revocation})
        self._rollback_if_active(state, model_ref, "model_revoked")
        self._write(self.catalogue_path, state)
        return revocation

    def set_availability(
        self,
        model_ref: str,
        *,
        status: str,
        reason: str,
        identity: DeviceIdentity,
    ) -> Dict[str, Any]:
        """Apply an issuer-signed non-qualification lifecycle state.

        Qualification remains evidence-driven; an operator cannot manually promote a
        model to ``qualified`` through this lifecycle control.
        """
        if status not in {"experimental", "unavailable", "deprecated"}:
            raise ValueError("model_lifecycle_transition_not_allowed")
        if not str(reason).strip():
            raise ValueError("model_lifecycle_reason_required")
        state = self._state()
        record = self._require(state, model_ref)
        if identity.public_key_b64 != record["manifest"]["issuer_public_key"]:
            raise PermissionError("model_lifecycle_issuer_mismatch")
        event = {
            "model_ref": model_ref,
            "manifest_hash": record["manifest_hash"],
            "previous_status": record.get("status") or "experimental",
            "status": status,
            "reason": str(reason).strip(),
            "changed_at": utc_now_iso(),
            "issuer_public_key": identity.public_key_b64,
        }
        event["signature"] = identity.sign(canonical_bytes(event))
        record["status"] = status
        record.setdefault("lifecycle_events", []).append(event)
        if status in {"unavailable", "deprecated"}:
            self._rollback_if_active(state, model_ref, f"model_{status}")
        self._write(self.catalogue_path, state)
        return event

    def compatibility(self, model_ref: str, hardware: Dict[str, Any], *, engine: str) -> Dict[str, Any]:
        manifest = self.record(model_ref)["manifest"]
        requirements = dict(manifest.get("compatibility") or {})
        reasons = []
        if int(hardware.get("memory_bytes") or 0) < int(requirements.get("minimum_memory_bytes") or 0): reasons.append("insufficient_memory")
        if int(hardware.get("storage_free_bytes") or 0) < int(requirements.get("minimum_storage_bytes") or 0): reasons.append("insufficient_storage")
        if requirements.get("architectures") and hardware.get("architecture") not in requirements["architectures"]: reasons.append("architecture_not_supported")
        if requirements.get("accelerators") and hardware.get("accelerator_class") not in requirements["accelerators"]: reasons.append("accelerator_not_supported")
        if requirements.get("engines") and engine not in requirements["engines"]: reasons.append("inference_engine_not_supported")
        return {"compatible": not reasons, "reasons": reasons, "model_ref": model_ref, "engine": engine}

    def verify_artifact(self, model_ref: str, artifact_path: str | Path) -> Dict[str, Any]:
        artifact = dict(self.record(model_ref)["manifest"].get("artifact") or {})
        path = Path(artifact_path)
        if not path.is_file(): return {"verified": False, "reason": "artifact_missing"}
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        raw_hash = digest.hexdigest()
        verified = raw_hash == str(artifact.get("sha256") or "") and path.stat().st_size == int(artifact.get("bytes") or -1)
        return {"verified": verified, "reason": "verified" if verified else "artifact_integrity_mismatch", "sha256": raw_hash, "bytes": path.stat().st_size}

    def record_benchmark(self, model_ref: str, *, suite_id: str, visibility: str, scores: Dict[str, Any], provenance: Dict[str, Any], customer_id: str = "") -> Dict[str, Any]:
        if visibility not in {"public", "customer_private"}: raise ValueError("benchmark_visibility_invalid")
        missing = [metric for metric in BENCHMARK_METRICS if metric not in scores]
        if missing: raise ValueError(f"benchmark_metrics_missing:{','.join(missing)}")
        event = {"schema_version": "aion.model_benchmark.v1", "model_ref": model_ref, "suite_id": suite_id, "visibility": visibility, "scores": dict(scores), "provenance": dict(provenance), "recorded_at": utc_now_iso()}
        if visibility == "customer_private":
            if not str(customer_id).strip():
                raise ValueError("customer_id_required_for_private_benchmark")
            event["customer_id"] = str(customer_id)
        event["benchmark_hash"] = canonical_hash(event)
        state = self._state(); record = self._require(state, model_ref)
        if visibility == "public":
            record.setdefault("public_benchmarks", []).append(event); self._write(self.catalogue_path, state)
        else:
            private = self._private(); private.setdefault("outcomes", []).append(event); self._write(self.private_scores_path, private, mode=0o600)
        return event

    def qualify(self, model_ref: str, *, hardware: Dict[str, Any], engine: str, thresholds: Dict[str, float]) -> Dict[str, Any]:
        state = self._state(); record = self._require(state, model_ref)
        compatible = self.compatibility(model_ref, hardware, engine=engine)
        latest = (record.get("public_benchmarks") or [])[-1] if record.get("public_benchmarks") else None
        failures = list(compatible["reasons"])
        if not latest: failures.append("public_benchmark_required")
        else:
            for metric, threshold in thresholds.items():
                value = float((latest.get("scores") or {}).get(metric, 0))
                if metric in {"latency", "cost", "energy"}:
                    if value > float(threshold): failures.append(f"{metric}_maximum_exceeded")
                elif value < float(threshold): failures.append(f"{metric}_minimum_not_met")
        qualification = {"qualified": not failures, "failures": failures, "hardware_class": {key: hardware.get(key) for key in ("architecture", "memory_bytes", "accelerator_class")}, "engine": engine, "thresholds": thresholds, "evaluated_at": utc_now_iso()}
        qualification["qualification_hash"] = canonical_hash(qualification)
        record["qualification"] = qualification; record["status"] = "qualified" if not failures else "blocked"
        self._write(self.catalogue_path, state); return qualification

    def start_canary(self, *, task_class: str, champion: str, challenger: str, percentage: int, maximum_requests: int, thresholds: Dict[str, float]) -> Dict[str, Any]:
        state = self._state(); self._require_qualified(state, champion); self._require_qualified(state, challenger)
        existing = dict((state.get("routes") or {}).get(task_class) or {})
        if existing.get("champion") and existing["champion"] != champion:
            raise ValueError("declared_champion_does_not_match_active_route")
        if not 1 <= percentage <= 20: raise ValueError("canary_percentage_out_of_range")
        if not 1 <= maximum_requests <= 1000: raise ValueError("canary_request_limit_out_of_range")
        canary = {"task_class": task_class, "champion": champion, "challenger": challenger, "percentage": percentage, "maximum_requests": maximum_requests, "thresholds": thresholds, "samples": [], "status": "running", "started_at": utc_now_iso()}
        canary["canary_id"] = f"canary_{canonical_hash(canary)[:20]}"
        state.setdefault("routes", {})[task_class] = {"champion": champion, "previous_champion": "", "canary": canary}
        self._write(self.catalogue_path, state); return canary

    def record_canary_sample(self, task_class: str, *, champion_scores: Dict[str, float], challenger_scores: Dict[str, float]) -> Dict[str, Any]:
        state = self._state(); route = dict((state.get("routes") or {}).get(task_class) or {}); canary = dict(route.get("canary") or {})
        if canary.get("status") != "running": raise ValueError("active_canary_required")
        canary.setdefault("samples", []).append({"champion": champion_scores, "challenger": challenger_scores, "recorded_at": utc_now_iso()})
        route["canary"] = canary; state["routes"][task_class] = route
        if len(canary["samples"]) >= int(canary["maximum_requests"]): self._evaluate_canary(route)
        self._write(self.catalogue_path, state); return route

    def rollback(self, task_class: str, *, reason: str) -> Dict[str, Any]:
        state = self._state(); route = dict((state.get("routes") or {}).get(task_class) or {})
        previous = str(route.get("previous_champion") or "")
        if not previous: raise ValueError("previous_champion_unavailable")
        route.update({"champion": previous, "previous_champion": "", "rollback": {"reason": reason, "at": utc_now_iso()}})
        state.setdefault("routes", {})[task_class] = route; self._write(self.catalogue_path, state); return route

    def detect_drift(self, model_ref: str, *, baseline: Dict[str, float], current: Dict[str, float], tolerances: Dict[str, float], provider_fingerprint_before: str = "", provider_fingerprint_now: str = "") -> Dict[str, Any]:
        regressions = []
        for metric, old in baseline.items():
            new = float(current.get(metric, 0)); tolerance = float(tolerances.get(metric, 0))
            if metric in {"latency", "cost", "energy"}:
                if new > float(old) + tolerance: regressions.append(metric)
            elif new < float(old) - tolerance: regressions.append(metric)
        provider_changed = bool(provider_fingerprint_before and provider_fingerprint_now and provider_fingerprint_before != provider_fingerprint_now)
        report = {"model_ref": model_ref, "drift_detected": bool(regressions or provider_changed), "regressions": regressions, "provider_behavior_changed": provider_changed, "checked_at": utc_now_iso()}
        if report["drift_detected"]:
            state = self._state(); record = self._require(state, model_ref); record["status"] = "blocked"; record["drift"] = report; self._rollback_if_active(state, model_ref, "regression_or_provider_drift"); self._write(self.catalogue_path, state)
        return report

    def mirror_plan(self, active_profiles: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        state = self._state(); required = {str(item.get("model_ref")) for item in active_profiles if item.get("active") is True}
        artifacts = []
        for ref in sorted(required):
            record = (state.get("models") or {}).get(ref)
            if not record or record.get("status") == "blocked": continue
            manifest = record["manifest"]; licence = dict(manifest.get("licence") or {})
            if licence.get("redistribution_allowed") is not True: continue
            mirrors = list(manifest.get("mirrors") or [])
            if mirrors: artifacts.append({"model_ref": ref, "manifest_hash": record["manifest_hash"], "artifact": manifest["artifact"], "mirror": mirrors[0]})
        return {"schema_version": "aion.model_mirror_plan.v1", "artifacts": artifacts, "active_profile_count": len(required), "generated_at": utc_now_iso()}

    def installation_check(self, model_ref: str, *, hardware: Dict[str, Any], engine: str, artifact_path: str | Path) -> Dict[str, Any]:
        """Fail-closed preflight before a model artefact can enter an active pack."""
        record = self.record(model_ref)
        compatibility = self.compatibility(model_ref, hardware, engine=engine)
        integrity = self.verify_artifact(model_ref, artifact_path)
        licence = dict(record["manifest"].get("licence") or {})
        failures = list(compatibility["reasons"])
        if not integrity["verified"]:
            failures.append(integrity["reason"])
        if licence.get("commercial_use_allowed") is not True:
            failures.append("commercial_use_not_permitted")
        return {
            "installable": not failures,
            "model_ref": model_ref,
            "failures": failures,
            "compatibility": compatibility,
            "integrity": integrity,
            "licence_id": licence.get("id"),
        }

    def preflight(self, model_ref: str, *, hardware: Dict[str, Any], engine: str) -> Dict[str, Any]:
        """Return bounded, non-secret information suitable for the Node Editor."""
        record = self.record(model_ref)
        manifest = record["manifest"]
        compatibility = self.compatibility(model_ref, hardware, engine=engine)
        status = str(record.get("status") or "experimental")
        allowed = compatibility["compatible"] and status not in {"blocked", "unavailable", "deprecated"}
        result = {
            "schema_version": "aion.model_preflight.v1",
            "model_ref": model_ref,
            "status": status,
            "selectable": allowed,
            "compatibility": compatibility,
            "capabilities": dict(manifest.get("capabilities") or {}),
            "estimates": dict(manifest.get("estimates") or {}),
            "licence": {
                key: (manifest.get("licence") or {}).get(key)
                for key in ("id", "commercial_use_allowed", "attribution_required", "source")
            },
            "credentials_exposed": False,
            "customer_content_exposed": False,
        }
        result["preflight_hash"] = canonical_hash(result)
        return result

    def admin_catalogue(self) -> Dict[str, Any]:
        state = self._state(); groups = {status: [] for status in MODEL_LIFECYCLE_STATES}
        for ref, record in sorted((state.get("models") or {}).items()):
            manifest = record["manifest"]
            groups.setdefault(record.get("status") or "experimental", []).append({
                "model_ref": ref,
                "status": record.get("status"),
                "provider": manifest.get("provider"),
                "execution": manifest.get("execution"),
                "capabilities": manifest.get("capabilities"),
                "licence": manifest.get("licence"),
                "estimates": manifest.get("estimates"),
                "qualification": record.get("qualification"),
                "public_benchmarks": record.get("public_benchmarks", []),
                "revoked": bool(record.get("revocation")),
            })
        return {"schema_version": "aion.model_admin_catalogue.v1", "groups": groups, "routes": state.get("routes", {}), "customer_private_outcomes_exposed": False}

    def record(self, model_ref: str) -> Dict[str, Any]: return self._require(self._state(), model_ref)

    def _evaluate_canary(self, route: Dict[str, Any]) -> None:
        canary = route["canary"]; samples = canary["samples"]; thresholds = canary["thresholds"]
        def average(side: str, metric: str) -> float: return sum(float((item[side] or {}).get(metric, 0)) for item in samples) / len(samples)
        passed = True
        for metric, threshold in thresholds.items():
            challenger = average("challenger", metric); champion = average("champion", metric)
            if metric in {"latency", "cost", "energy"}:
                metric_passed = challenger <= float(threshold) and challenger <= champion
            else:
                metric_passed = challenger >= float(threshold) and challenger >= champion
            passed = passed and metric_passed
        canary["status"] = "promoted" if passed else "rejected"; canary["completed_at"] = utc_now_iso()
        if passed: route["previous_champion"] = route["champion"]; route["champion"] = canary["challenger"]

    def _rollback_if_active(self, state: Dict[str, Any], model_ref: str, reason: str) -> None:
        for task_class, route in (state.get("routes") or {}).items():
            if route.get("champion") == model_ref and route.get("previous_champion"):
                route["champion"], route["previous_champion"] = route["previous_champion"], ""; route["rollback"] = {"reason": reason, "at": utc_now_iso()}

    @staticmethod
    def _validate_manifest(manifest: Dict[str, Any]) -> None:
        required = (
            "model_id", "version", "provider", "artifact", "licence", "mirrors",
            "compatibility", "execution", "capabilities", "estimates",
            "issuer_public_key", "manifest_hash", "signature",
        )
        missing = [key for key in required if not manifest.get(key)]
        if missing: raise ValueError(f"model_manifest_fields_missing:{','.join(missing)}")
        artifact = manifest["artifact"]
        if len(str(artifact.get("sha256") or "")) != 64 or int(artifact.get("bytes") or 0) <= 0: raise ValueError("model_artifact_identity_invalid")
        licence = manifest["licence"]
        if (
            not licence.get("id")
            or "commercial_use_allowed" not in licence
            or "redistribution_allowed" not in licence
            or not licence.get("source")
            or "attribution_required" not in licence
        ):
            raise ValueError("model_licence_declaration_required")
        execution = dict(manifest.get("execution") or {})
        if execution.get("adapter_family") not in {
            "llama_cpp", "ollama", "openai_compatible", "gemini", "anthropic", "nvidia_nim"
        }:
            raise ValueError("model_adapter_family_not_supported")
        capabilities = dict(manifest.get("capabilities") or {})
        capability_required = ("modalities", "context_tokens", "structured_output", "tools", "languages", "domains")
        if any(key not in capabilities for key in capability_required):
            raise ValueError("model_capability_declaration_required")
        if not isinstance(capabilities.get("modalities"), list) or not capabilities["modalities"]:
            raise ValueError("model_modality_required")
        if int(capabilities.get("context_tokens") or 0) <= 0:
            raise ValueError("model_context_limit_invalid")
        estimates = dict(manifest.get("estimates") or {})
        if any(key not in estimates for key in ("latency_ms", "cost_per_million_input_tokens", "energy_wh_per_request")):
            raise ValueError("model_estimates_required")

    @staticmethod
    def _require(state: Dict[str, Any], model_ref: str) -> Dict[str, Any]:
        record = (state.get("models") or {}).get(model_ref)
        if not record: raise KeyError("model_not_registered")
        return record

    def _require_qualified(self, state: Dict[str, Any], model_ref: str) -> None:
        if self._require(state, model_ref).get("status") != "qualified": raise PermissionError("qualified_model_required")

    def _state(self) -> Dict[str, Any]:
        if not self.catalogue_path.exists(): return {"schema_version": "aion.model_catalogue.v1", "models": {}, "routes": {}}
        return json.loads(self.catalogue_path.read_text(encoding="utf-8"))

    def _private(self) -> Dict[str, Any]:
        if not self.private_scores_path.exists(): return {"schema_version": "aion.customer_private_model_outcomes.v1", "outcomes": []}
        return json.loads(self.private_scores_path.read_text(encoding="utf-8"))

    @staticmethod
    def _write(path: Path, payload: Dict[str, Any], *, mode: int = 0o644) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        os.chmod(temporary, mode)
        os.replace(temporary, path)
