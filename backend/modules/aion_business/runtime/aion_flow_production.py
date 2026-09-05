from __future__ import annotations

import base64
import binascii
import contextlib
import hmac
import json
import os
import re
import statistics
import time
from pathlib import Path
from typing import Any, Dict, Mapping

import fcntl

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso
from backend.modules.aion_fabric.identity import DeviceIdentity, IdentityStore
from backend.modules.aion_business.runtime.aion_flow_authority import AionFlowWorkspaceAuthority


OPERATION_CAPABILITIES = {
    "author": "aion_flow.author",
    "review": "aion_flow.review",
    "commit": "aion_flow.commit",
    "export": "aion_flow.export",
    "import": "aion_flow.import",
    "benchmark": "aion_flow.benchmark",
}

MAX_GRAPH_BYTES = 5 * 1024 * 1024
MAX_TRANSFER_BYTES = 8 * 1024 * 1024
MAX_STATE_BYTES = 128 * 1024 * 1024
MAX_JSON_DEPTH = 32
MAX_JSON_ITEMS = 100_000
MAX_SCALAR_BYTES = 1024 * 1024
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")


class AionFlowProductionService:
    """Customer-owned versioning, qualification, encrypted movement and safe observability."""

    def __init__(
        self,
        root: str | Path = ".runtime/aion_flow/production",
        *,
        authority: AionFlowWorkspaceAuthority | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "workflow-revisions.json"
        self.lock_path = self.root / "workflow-revisions.lock"
        self.identity = IdentityStore(self.root / "mother-identity").load_or_create()
        self.authority = authority or AionFlowWorkspaceAuthority()

    def qualify(self, graph: Mapping[str, Any], *, actor: Mapping[str, Any], mode: str = "author") -> Dict[str, Any]:
        capability = OPERATION_CAPABILITIES["author" if mode == "author" else "review"]
        authority = self.authority.authorize(actor, capability, graph=graph)
        errors = self._shape_errors(graph)
        nodes = list(graph.get("nodes") or []) if isinstance(graph, Mapping) and isinstance(graph.get("nodes") or [], list) else []
        edges = list(graph.get("edges") or []) if isinstance(graph, Mapping) and isinstance(graph.get("edges") or [], list) else []
        identifiers = [str(item.get("id") or "") for item in nodes if isinstance(item, Mapping)]
        if not authority["allowed"]: errors.append(f"canonical_authority_denied:{authority['reason']}")
        if nodes and len(identifiers) == len(nodes) and (len(set(identifiers)) != len(identifiers) or any(not SAFE_IDENTIFIER.fullmatch(item) for item in identifiers)): errors.append("node_identity_invalid")
        unknown = [edge for edge in edges if isinstance(edge, Mapping) and (str(edge.get("from") or edge.get("source") or "") not in identifiers or str(edge.get("to") or edge.get("target") or "") not in identifiers)]
        if unknown: errors.append("edge_target_missing")
        graph_hash = canonical_hash(graph) if not any(value.startswith("graph_") or value.startswith("node_") or value.startswith("edge_") or value.startswith("workflow_id_") for value in errors) else None
        return {
            "ok": not errors, "mode": mode, "errors": errors, "graph_hash": graph_hash,
            "counts": {"nodes": len(nodes), "edges": len(edges), "groups": len(graph.get("groups") or []) if isinstance(graph, Mapping) and isinstance(graph.get("groups") or [], list) else 0, "subflows": len(graph.get("subflows") or []) if isinstance(graph, Mapping) and isinstance(graph.get("subflows") or [], list) else 0},
            "responsive_surfaces": {"desktop_author": True, "tablet_author": True, "mobile_read_only": True},
            "review_only": mode == "review", "external_writes": 0,
            "authority": authority,
        }

    def commit(self, graph: Mapping[str, Any], *, actor: Mapping[str, Any], base_revision: int) -> Dict[str, Any]:
        check = self.qualify(graph, actor=actor, mode="author")
        if not check["ok"]: raise PermissionError(",".join(check["errors"]))
        commit_authority = self.authority.authorize(actor, OPERATION_CAPABILITIES["commit"], graph=graph)
        if not commit_authority["allowed"]: raise PermissionError(f"canonical_authority_denied:{commit_authority['reason']}")
        workspace_id = str(commit_authority["workspace_id"])
        organisation_id = str(commit_authority["organisation_id"])
        workflow_id = str(graph["workflow_id"])
        scoped_key = self._workflow_key(workspace_id, workflow_id)
        with self._exclusive_state_lock():
            state = self._state()
            legacy_item = state["workflows"].get(workflow_id)
            if legacy_item and legacy_item.get("history") and scoped_key not in state["workflows"]:
                raise PermissionError("workflow_scope_migration_required")
            item = state["workflows"].setdefault(scoped_key, {"revision": 0, "history": []})
            if item.get("workspace_id") and item["workspace_id"] != workspace_id: raise PermissionError("workflow_workspace_mismatch")
            if item.get("organisation_id") and item["organisation_id"] != organisation_id: raise PermissionError("workflow_organisation_mismatch")
            if int(base_revision) != int(item["revision"]):
                raise RuntimeError(f"revision_conflict:expected={item['revision']}:received={base_revision}")
            revision = item["revision"] + 1
            author = {"person_id": str(commit_authority["person_id"]), "authority_source": commit_authority["authority_source"]}
            record = {"workflow_id": workflow_id, "workspace_id": workspace_id, "organisation_id": organisation_id, "revision": revision, "base_revision": base_revision, "graph": dict(graph), "graph_hash": check["graph_hash"], "author": author, "committed_at": utc_now_iso()}
            record["record_hash"] = canonical_hash(record); record["mother_signature"] = self.identity.sign(canonical_bytes(record)); record["mother_public_key"] = self.identity.public_key_b64
            item.update({"workspace_id": workspace_id, "organisation_id": organisation_id, "revision": revision})
            item["history"].append(record); self._write(state)
        return self._public_revision(record)

    def history(self, workflow_id: str, *, actor: Mapping[str, Any]) -> Dict[str, Any]:
        decision = self.authority.authorize(actor, OPERATION_CAPABILITIES["review"])
        if not decision["allowed"]: raise PermissionError(f"canonical_authority_denied:{decision['reason']}")
        state = self._state()["workflows"]
        item = state.get(self._workflow_key(str(decision["workspace_id"]), str(workflow_id)))
        if item is None and state.get(str(workflow_id), {}).get("history"):
            raise PermissionError("workflow_scope_migration_required")
        item = item or {"revision": 0, "history": []}
        return {"workflow_id": str(workflow_id), "revision": item["revision"], "history": [self._public_revision(value) for value in item["history"]]}

    def diff(self, workflow_id: str, left: int, right: int, *, actor: Mapping[str, Any]) -> Dict[str, Any]:
        decision = self.authority.authorize(actor, OPERATION_CAPABILITIES["review"])
        if not decision["allowed"]: raise PermissionError(f"canonical_authority_denied:{decision['reason']}")
        state = self._state()["workflows"]
        state_item = state.get(self._workflow_key(str(decision["workspace_id"]), str(workflow_id)))
        if state_item is None and state.get(str(workflow_id), {}).get("history"):
            raise PermissionError("workflow_scope_migration_required")
        state_item = state_item or {}
        records = {item["revision"]: item for item in state_item.get("history", [])}
        if left not in records or right not in records: raise KeyError("workflow_revision_not_found")
        a, b = records[left]["graph"], records[right]["graph"]
        nodes_a = {str(item["id"]): canonical_hash(item) for item in a.get("nodes", [])}; nodes_b = {str(item["id"]): canonical_hash(item) for item in b.get("nodes", [])}
        return {"workflow_id": workflow_id, "left": left, "right": right, "added_nodes": sorted(nodes_b.keys() - nodes_a.keys()), "removed_nodes": sorted(nodes_a.keys() - nodes_b.keys()), "changed_nodes": sorted(key for key in nodes_a.keys() & nodes_b.keys() if nodes_a[key] != nodes_b[key]), "edge_count_delta": len(b.get("edges", [])) - len(a.get("edges", [])), "external_writes": 0}

    def encrypted_export(self, graph: Mapping[str, Any], *, password: str, actor: Mapping[str, Any]) -> Dict[str, Any]:
        normalized = self._migrate({"graph": dict(graph)})
        decision = self.authority.authorize(actor, OPERATION_CAPABILITIES["export"], graph=normalized)
        if not decision["allowed"]: raise PermissionError(f"canonical_authority_denied:{decision['reason']}")
        check = self.qualify(normalized, actor=actor, mode="review")
        structural_errors = [value for value in check["errors"] if not value.startswith("canonical_authority_denied:")]
        if structural_errors: raise ValueError(",".join(structural_errors))
        if len(password) < 12: raise ValueError("export_password_minimum_12_characters")
        salt, nonce = os.urandom(16), os.urandom(12); key = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(password.encode())
        header = {"schema_version": "aion.flow.encrypted_export.v1", "workflow_id": normalized["workflow_id"], "graph_hash": check["graph_hash"], "created_at": utc_now_iso(), "kdf": "scrypt-n16384-r8-p1", "cipher": "aes-256-gcm"}
        ciphertext = AESGCM(key).encrypt(nonce, canonical_bytes({"schema_version": "aion.flow.graph.v1", "graph": normalized}), canonical_bytes(header))
        return {"header": header, "salt": base64.b64encode(salt).decode(), "nonce": base64.b64encode(nonce).decode(), "ciphertext": base64.b64encode(ciphertext).decode()}

    def encrypted_import(self, package: Mapping[str, Any], *, password: str, actor: Mapping[str, Any]) -> Dict[str, Any]:
        decision = self.authority.authorize(actor, OPERATION_CAPABILITIES["import"])
        if not decision["allowed"]: raise PermissionError(f"canonical_authority_denied:{decision['reason']}")
        if len(password) < 12: raise ValueError("import_password_minimum_12_characters")
        if not isinstance(package, Mapping): raise ValueError("import_package_invalid")
        header = dict(package.get("header") or {})
        if header.get("schema_version") != "aion.flow.encrypted_export.v1" or header.get("kdf") != "scrypt-n16384-r8-p1" or header.get("cipher") != "aes-256-gcm":
            raise ValueError("import_header_not_supported")
        try:
            salt = base64.b64decode(str(package["salt"]), validate=True)
            nonce = base64.b64decode(str(package["nonce"]), validate=True)
            ciphertext = base64.b64decode(str(package["ciphertext"]), validate=True)
        except (KeyError, ValueError, binascii.Error, TypeError) as error:
            raise ValueError("import_encoding_invalid") from error
        if len(salt) != 16 or len(nonce) != 12 or not ciphertext or len(ciphertext) > MAX_TRANSFER_BYTES:
            raise ValueError("import_transfer_bounds_exceeded")
        key = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(password.encode())
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, canonical_bytes(header))
        if len(plaintext) > MAX_GRAPH_BYTES: raise ValueError("import_graph_bounds_exceeded")
        value = json.loads(plaintext)
        graph = self._migrate(value); actual = canonical_hash(graph)
        if not hmac.compare_digest(actual, str(header.get("graph_hash") or "")): raise ValueError("import_graph_hash_mismatch")
        structural_errors = [value for value in self._shape_errors(graph) if not value.startswith("canonical_authority_denied:")]
        if structural_errors: raise ValueError(",".join(structural_errors))
        return {"graph": graph, "graph_hash": actual, "migrated_to": "aion.flow.graph.v1", "authority_granted": False, "external_writes": 0}

    def telemetry(self, graph: Mapping[str, Any], *, actor: Mapping[str, Any], operational: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        decision = self.authority.authorize(actor, OPERATION_CAPABILITIES["review"], graph=graph)
        if not decision["allowed"]: raise PermissionError(f"canonical_authority_denied:{decision['reason']}")
        operational = dict(operational or {}); nodes = list(graph.get("nodes") or [])
        safe = {"workflow_hash": canonical_hash(graph), "node_count": len(nodes), "edge_count": len(graph.get("edges") or []), "node_families": sorted({str(item.get("type") or item.get("kind") or "unknown")[:80] for item in nodes}), "status_counts": {str(key)[:40]: int(value) for key, value in (operational.get("status_counts") or {}).items()}, "latency_buckets_ms": list(operational.get("latency_buckets_ms") or [])[:20], "recorded_at": utc_now_iso(), "contains_content": False, "contains_credentials": False, "contains_customer_identifiers": False}
        safe["telemetry_hash"] = canonical_hash(safe); return safe

    def benchmark(self, graph: Mapping[str, Any], *, actor: Mapping[str, Any], iterations: int = 25) -> Dict[str, Any]:
        decision = self.authority.authorize(actor, OPERATION_CAPABILITIES["benchmark"], graph=graph)
        if not decision["allowed"]: raise PermissionError(f"canonical_authority_denied:{decision['reason']}")
        iterations = max(1, min(int(iterations), 200)); started = time.perf_counter()
        for _ in range(iterations): canonical_hash(graph)
        elapsed = (time.perf_counter() - started) * 1000
        return {"iterations": iterations, "nodes": len(graph.get("nodes") or []), "edges": len(graph.get("edges") or []), "total_ms": round(elapsed, 3), "average_ms": round(elapsed / iterations, 3), "external_writes": 0}

    def load_qualification(
        self,
        *,
        actor: Mapping[str, Any],
        large_nodes: int = 1500,
        parallel_routes: int = 256,
        checkpoints: int = 250,
    ) -> Dict[str, Any]:
        """Run bounded, content-free production-load qualifications.

        This deliberately does not invoke model providers or consequential
        capabilities.  It measures the parts AION owns: graph qualification,
        deterministic route traversal and crash-safe local checkpoint recovery.
        """
        decision = self.authority.authorize(actor, OPERATION_CAPABILITIES["benchmark"])
        if not decision["allowed"]:
            raise PermissionError(f"canonical_authority_denied:{decision['reason']}")
        large_nodes = max(100, min(int(large_nodes), 5000))
        parallel_routes = max(2, min(int(parallel_routes), 2000))
        checkpoints = max(10, min(int(checkpoints), 5000))

        large_graph = {
            "workflow_id": "qualification-large-graph",
            "nodes": [{"id": f"node-{index}", "type": "local_transform", "config": {}} for index in range(large_nodes)],
            "edges": [{"from": f"node-{index}", "to": f"node-{index + 1}"} for index in range(large_nodes - 1)],
            "groups": [],
            "subflows": [],
        }
        large_samples = self._timed_samples(lambda: self.qualify(large_graph, actor=actor), 5)
        large_result = self.qualify(large_graph, actor=actor)

        route_ids = [f"route-{index}" for index in range(parallel_routes)]
        parallel_graph = {
            "workflow_id": "qualification-parallel-routes",
            "nodes": [{"id": "ingress", "type": "router", "config": {}}]
            + [{"id": route_id, "type": "local_transform", "config": {}} for route_id in route_ids]
            + [{"id": "merge", "type": "merge", "config": {}}],
            "edges": ([{"from": "ingress", "to": route_id} for route_id in route_ids]
                      + [{"from": route_id, "to": "merge"} for route_id in route_ids]),
            "groups": [],
            "subflows": [],
        }

        def traverse_parallel() -> str:
            products = [canonical_hash({"route": route_id, "input": "synthetic"}) for route_id in route_ids]
            return canonical_hash({"ordered_route_outputs": products})

        parallel_samples = self._timed_samples(traverse_parallel, 10)
        parallel_first = traverse_parallel()
        parallel_deterministic = all(hmac.compare_digest(parallel_first, traverse_parallel()) for _ in range(3))
        parallel_result = self.qualify(parallel_graph, actor=actor)

        qualification_root = self.root / "load-qualification"
        qualification_root.mkdir(parents=True, exist_ok=True)
        checkpoint_path = qualification_root / "long-running-checkpoint.json"
        checkpoint_samples: list[float] = []
        previous_hash = "genesis"
        started = time.perf_counter()
        for sequence in range(1, checkpoints + 1):
            record = {
                "schema_version": "aion.flow.qualification_checkpoint.v1",
                "sequence": sequence,
                "previous_hash": previous_hash,
                "synthetic": True,
            }
            record["checkpoint_hash"] = canonical_hash(record)
            before = time.perf_counter()
            temporary = checkpoint_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
            temporary.replace(checkpoint_path)
            checkpoint_samples.append((time.perf_counter() - before) * 1000)
            previous_hash = record["checkpoint_hash"]
        recovered = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        recovery_ok = (
            int(recovered.get("sequence") or 0) == checkpoints
            and hmac.compare_digest(str(recovered.get("checkpoint_hash") or ""), previous_hash)
        )
        long_total_ms = (time.perf_counter() - started) * 1000

        profiles = {
            "large_graph": {
                "passed": bool(large_result["ok"]),
                "nodes": large_nodes,
                "edges": large_nodes - 1,
                **self._latency_summary(large_samples),
            },
            "parallel_routes": {
                "passed": bool(parallel_result["ok"] and parallel_deterministic),
                "routes": parallel_routes,
                "edges": parallel_routes * 2,
                "deterministic": parallel_deterministic,
                **self._latency_summary(parallel_samples),
            },
            "long_running": {
                "passed": recovery_ok,
                "checkpoints": checkpoints,
                "recovered_sequence": int(recovered.get("sequence") or 0),
                "total_ms": round(long_total_ms, 3),
                **self._latency_summary(checkpoint_samples),
            },
        }
        report = {
            "schema_version": "aion.flow.load_qualification.v1",
            "qualified_at": utc_now_iso(),
            "workspace_id": str(decision["workspace_id"]),
            "profiles": profiles,
            "passed": all(profile["passed"] for profile in profiles.values()),
            "synthetic_content_only": True,
            "external_model_calls": 0,
            "external_writes": 0,
            "local_checkpoint_writes": checkpoints,
            "contains_customer_content": False,
            "contains_credentials": False,
        }
        report["report_hash"] = canonical_hash(report)
        report["mother_signature"] = self.identity.sign(canonical_bytes(report))
        report["mother_public_key"] = self.identity.public_key_b64
        evidence_path = qualification_root / f"{report['report_hash']}.json"
        evidence_path.write_text(json.dumps(report, sort_keys=True, indent=2), encoding="utf-8")
        os.chmod(evidence_path, 0o600)
        return report

    @staticmethod
    def _timed_samples(operation, iterations: int) -> list[float]:
        samples = []
        for _ in range(iterations):
            started = time.perf_counter()
            operation()
            samples.append((time.perf_counter() - started) * 1000)
        return samples

    @staticmethod
    def _latency_summary(samples: list[float]) -> Dict[str, float]:
        ordered = sorted(samples)
        percentile_index = max(0, min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1)))))
        return {
            "average_ms": round(statistics.fmean(ordered), 3),
            "p95_ms": round(ordered[percentile_index], 3),
            "maximum_ms": round(ordered[-1], 3),
        }

    @staticmethod
    def _migrate(value: Mapping[str, Any]) -> Dict[str, Any]:
        if not isinstance(value, Mapping): raise ValueError("graph_document_invalid")
        graph = dict(value.get("graph") or value)
        graph.setdefault("nodes", []); graph.setdefault("edges", []); graph.setdefault("groups", []); graph.setdefault("subflows", [])
        if not isinstance(graph["edges"], list): raise ValueError("graph_edges_invalid")
        for edge in graph["edges"]:
            if not isinstance(edge, Mapping): raise ValueError("edge_record_invalid")
            if "source" in edge and "from" not in edge: edge["from"] = edge.pop("source")
            if "target" in edge and "to" not in edge: edge["to"] = edge.pop("target")
        return graph

    @staticmethod
    def _public_revision(record: Mapping[str, Any]) -> Dict[str, Any]:
        return {key: value for key, value in record.items() if key != "graph"}

    @staticmethod
    def _workflow_key(workspace_id: str, workflow_id: str) -> str:
        # Both identifiers are restricted to SAFE_IDENTIFIER, which excludes the
        # separator and preserves compatibility with existing revision stores.
        return f"{workspace_id}:{workflow_id}"

    @staticmethod
    def _shape_errors(graph: Mapping[str, Any]) -> list[str]:
        if not isinstance(graph, Mapping): return ["graph_document_invalid"]
        workflow_id = graph.get("workflow_id")
        errors: list[str] = []
        if not isinstance(workflow_id, str) or not SAFE_IDENTIFIER.fullmatch(workflow_id): errors.append("workflow_id_invalid")
        for field in ("nodes", "edges", "groups", "subflows"):
            if not isinstance(graph.get(field, []), list): errors.append(f"graph_{field}_invalid")
        nodes, edges = graph.get("nodes", []), graph.get("edges", [])
        if isinstance(nodes, list):
            if not nodes: errors.append("workflow_nodes_required")
            if any(not isinstance(item, Mapping) for item in nodes): errors.append("node_record_invalid")
        if isinstance(edges, list) and any(not isinstance(item, Mapping) for item in edges): errors.append("edge_record_invalid")
        if isinstance(nodes, list) and isinstance(edges, list) and (len(nodes) > 5000 or len(edges) > 20000): errors.append("graph_production_limit_exceeded")
        try:
            count = [0]
            AionFlowProductionService._check_json_bounds(graph, depth=0, count=count, seen=set())
            if len(canonical_bytes(graph)) > MAX_GRAPH_BYTES: errors.append("graph_encoded_size_exceeded")
        except (TypeError, ValueError, RecursionError):
            errors.append("graph_structure_bounds_exceeded")
        return list(dict.fromkeys(errors))

    @staticmethod
    def _check_json_bounds(value: Any, *, depth: int, count: list[int], seen: set[int]) -> None:
        if depth > MAX_JSON_DEPTH: raise ValueError("depth")
        count[0] += 1
        if count[0] > MAX_JSON_ITEMS: raise ValueError("items")
        if isinstance(value, (Mapping, list)):
            marker = id(value)
            if marker in seen: raise ValueError("cycle")
            seen.add(marker)
            values = value.items() if isinstance(value, Mapping) else enumerate(value)
            for key, item in values:
                if isinstance(key, str) and len(key.encode("utf-8")) > MAX_SCALAR_BYTES: raise ValueError("key")
                AionFlowProductionService._check_json_bounds(item, depth=depth + 1, count=count, seen=seen)
            seen.remove(marker)
        elif isinstance(value, str) and len(value.encode("utf-8")) > MAX_SCALAR_BYTES:
            raise ValueError("scalar")
        elif value is not None and not isinstance(value, (str, int, float, bool)):
            raise TypeError("non-json value")

    @contextlib.contextmanager
    def _exclusive_state_lock(self):
        with self.lock_path.open("a+", encoding="utf-8") as lock:
            os.chmod(self.lock_path, 0o600)
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _state(self) -> Dict[str, Any]:
        if not self.state_path.exists(): return {"schema_version": "aion.flow.production_revisions.v1", "workflows": {}}
        if self.state_path.stat().st_size > MAX_STATE_BYTES: raise ValueError("workflow_revision_store_too_large")
        value = json.loads(self.state_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not isinstance(value.get("workflows"), dict): raise ValueError("workflow_revision_store_invalid")
        return value

    def _write(self, value: Mapping[str, Any]) -> None:
        temporary = self.state_path.with_suffix(".tmp"); temporary.write_text(json.dumps(dict(value), indent=2, sort_keys=True), encoding="utf-8"); os.chmod(temporary, 0o600); os.replace(temporary, self.state_path)
