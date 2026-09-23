from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping

from backend.modules.aion_business.runtime.aion_flow_governance import AionFlowGovernancePlanner
from backend.modules.aion_business.runtime.sovereign_flow_compiler import SovereignFlowCompiler
from backend.modules.aion_fabric.canonical import canonical_hash, utc_now_iso
from backend.modules.workflow_capsules.connectors.workflow_connector_adapter import (
    WorkflowConnectorAdapter,
)


TERMINAL_STATES = {"verified", "failed", "cancelled", "compensated"}
ACTIVE_STATES = {"queued", "running", "waiting", "blocked"}
ALLOWED_CONTROL_ACTIONS = {"pause", "cancel", "resume", "recover"}


class AionFlowRunRepository:
    """Small customer-owned run journal; payloads are canonical JSON, never credentials."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root or ".runtime/aion_flow/runs")
        self.root.mkdir(parents=True, exist_ok=True)
        self.prepared_root = self.root.parent / "prepared"
        self.prepared_root.mkdir(parents=True, exist_ok=True)

    def save(self, run: Mapping[str, Any]) -> Dict[str, Any]:
        safe = _redact(dict(run))
        path = self.root / f"{safe['run_id']}.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(safe, sort_keys=True, indent=2), encoding="utf-8")
        temporary.replace(path)
        return safe

    def get(self, run_id: str) -> Dict[str, Any] | None:
        path = self.root / f"{_safe_id(run_id)}.json"
        if not path.exists():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None

    def list(self, limit: int = 50) -> list[Dict[str, Any]]:
        items = []
        for path in sorted(self.root.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]:
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(value, dict):
                    items.append(value)
            except (OSError, json.JSONDecodeError):
                continue
        return items

    def save_prepared(self, prepared: Mapping[str, Any]) -> Dict[str, Any]:
        safe = _redact(dict(prepared))
        preparation_id = str(safe.get("preparation_id") or f"prep_{uuid.uuid4().hex}")
        safe["preparation_id"] = preparation_id
        path = self.prepared_root / f"{_safe_id(preparation_id)}.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(safe, sort_keys=True, indent=2), encoding="utf-8")
        temporary.replace(path)
        return safe

    def get_prepared(self, preparation_id: str) -> Dict[str, Any] | None:
        path = self.prepared_root / f"{_safe_id(preparation_id)}.json"
        if not path.exists():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None


class AionFlowExecutionService:
    """Compile, preview and execute sovereign graphs through bounded capability adapters."""

    def __init__(
        self,
        *,
        repository: AionFlowRunRepository | None = None,
        capability_executor: Callable[..., Mapping[str, Any]] | None = None,
        workflow_connector_adapter: WorkflowConnectorAdapter | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.repository = repository or AionFlowRunRepository()
        self.workflow_connector_adapter = workflow_connector_adapter or WorkflowConnectorAdapter()
        self.capability_executor = capability_executor or self._default_capability_executor
        self.clock = clock

    def prepare(
        self,
        *,
        graph: Mapping[str, Any],
        actor: Mapping[str, Any],
        policy: Mapping[str, Any],
        approvals: Iterable[Mapping[str, Any]] = (),
        inputs: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        normalized = self._normalize_graph(graph)
        compiled = SovereignFlowCompiler().compile(normalized)
        if not compiled.ok:
            return {"ok": False, "phase": "compile", "errors": compiled.errors, "executed": False}

        static = self._static_validate(compiled.manifest)
        governance = AionFlowGovernancePlanner().preflight(
            graph=compiled.manifest, actor=actor, policy=policy, approvals=approvals
        )
        capsule = self._to_capsule(compiled.manifest)
        simulation = self._simulate(compiled.manifest, inputs or {})
        disclosure = self._disclosure_report(compiled.manifest, governance)
        executable = static["ok"] and governance["allowed"]
        review = {
            "schema_version": "aion.flow.exact_review.v1",
            "flow_id": compiled.manifest["flow_id"],
            "manifest_hash": compiled.manifest["manifest_hash"],
            "actor": {key: actor.get(key) for key in ("person_id", "organisation_id", "workspace_id", "role", "purpose")},
            "capabilities": [
                {
                    "node_id": node["id"],
                    "capability_id": node.get("capability_id") or node.get("action_id") or "unbound",
                    "consequential": bool(node.get("consequential") or node.get("causes_external_effect")),
                    "target": node.get("target") or node.get("connector") or "local",
                }
                for node in compiled.manifest["nodes"] if node.get("type") == "capability"
            ],
            "disclosure_report_hash": disclosure["report_hash"],
            "estimated_cost": disclosure["estimated_cost"],
            "approval_count": len(governance.get("approvals") or []),
            "executable": executable,
        }
        review["review_hash"] = canonical_hash(review)
        result = {
            "ok": static["ok"],
            "phase": "prepared",
            "executed": False,
            "manifest": compiled.manifest,
            "capsule": capsule,
            "static_validation": static,
            "governance": governance,
            "simulation": simulation,
            "dry_run": {"ok": static["ok"], "external_writes_performed": 0, "predicted": disclosure},
            "review": review,
            "authorization_context": {
                "actor": dict(actor),
                "policy": dict(policy),
            },
        }
        return self.repository.save_prepared(result)

    def authorize_prepared(
        self,
        *,
        prepared: Mapping[str, Any],
        review_hash: str,
        approver_person_id: str,
        exact_confirmed: bool,
    ) -> Dict[str, Any]:
        current = dict(prepared)
        review = dict(current.get("review") or {})
        if not exact_confirmed or review_hash != review.get("review_hash"):
            return {"ok": False, "error": "exact_review_required", "executed": False}
        context = dict(current.get("authorization_context") or {})
        actor = dict(context.get("actor") or {})
        policy = dict(context.get("policy") or {})
        manifest = dict(current.get("manifest") or {})
        if not approver_person_id.strip():
            return {"ok": False, "error": "approver_person_id_required", "executed": False}

        approvals = []
        for node in manifest.get("nodes") or []:
            if not node.get("requires_approval"):
                continue
            if node.get("separation_of_duty") is True and approver_person_id == actor.get("person_id"):
                return {"ok": False, "error": "separation_of_duty_requires_different_approver", "executed": False}
            approval_id = str(node.get("approval_id") or f"approval_{node['id']}")
            scope_hash = str(node.get("exact_scope_hash") or canonical_hash({"manifest_hash": manifest.get("manifest_hash"), "node_id": node["id"]}))
            node["approval_id"] = approval_id
            node["exact_scope_hash"] = scope_hash
            approvals.append({
                "approval_id": approval_id,
                "approved": True,
                "scope_hash": scope_hash,
                "approver_person_id": approver_person_id,
                "approved_at": utc_now_iso(),
            })
        governance = AionFlowGovernancePlanner().preflight(
            graph=manifest, actor=actor, policy=policy, approvals=approvals
        )
        current["manifest"] = manifest
        current["governance"] = governance
        current["approval_receipts"] = [
            {**item, "approval_hash": canonical_hash(item)} for item in approvals
        ]
        review["approval_count"] = len(approvals)
        review["executable"] = bool(current.get("static_validation", {}).get("ok") and governance.get("allowed"))
        review.pop("review_hash", None)
        review["review_hash"] = canonical_hash(review)
        current["review"] = review
        current["phase"] = "authorized" if review["executable"] else "authorization_blocked"
        current["executed"] = False
        saved = self.repository.save_prepared(current)
        return {"ok": review["executable"], "prepared": saved, "review": review, "governance": governance, "executed": False}

    def execute(
        self,
        *,
        prepared: Mapping[str, Any],
        review_hash: str,
        exact_confirmed: bool,
        inputs: Mapping[str, Any] | None = None,
        execution_mode: str = "connector_ready",
    ) -> Dict[str, Any]:
        review = dict(prepared.get("review") or {})
        if not exact_confirmed or not review_hash or review_hash != review.get("review_hash"):
            return {"ok": False, "phase": "review", "error": "exact_review_required", "executed": False}
        if not review.get("executable"):
            return {"ok": False, "phase": "governance", "error": "prepared_route_not_authorized", "executed": False}

        manifest = dict(prepared.get("manifest") or {})
        run_id = f"aflow_{uuid.uuid4().hex}"
        now = utc_now_iso()
        ordered = self._ordered_nodes(manifest)
        run = {
            "schema_version": "aion.flow.run.v1",
            "run_id": run_id,
            "flow_id": manifest.get("flow_id"),
            "manifest_hash": manifest.get("manifest_hash"),
            "review_hash": review_hash,
            "status": "running",
            "execution_mode": execution_mode,
            "created_at": now,
            "updated_at": now,
            "attempt": 1,
            "inputs_hash": canonical_hash(_redact(dict(inputs or {}))),
            "nodes": [self._node_state(node, index) for index, node in enumerate(ordered)],
            "events": [{"event": "run_started", "at": now}],
            "compensations": [],
            "authority_context": {
                key: (prepared.get("authorization_context") or {}).get("actor", {}).get(key)
                for key in ("person_id", "workspace_id", "organisation_id")
            },
        }
        self.repository.save(run)
        return self._continue(run, manifest=manifest, inputs=inputs or {})

    def control(self, run_id: str, action: str, *, prepared: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        action = str(action or "").strip().lower()
        if action not in ALLOWED_CONTROL_ACTIONS:
            return {"ok": False, "error": "control_action_not_allowed"}
        run = self.repository.get(run_id)
        if not run:
            return {"ok": False, "error": "run_not_found"}
        if action == "pause" and run["status"] not in TERMINAL_STATES:
            run["status"] = "waiting"
            self._event(run, "run_paused")
        elif action == "cancel" and run["status"] not in TERMINAL_STATES:
            run["status"] = "cancelled"
            self._event(run, "run_cancelled")
            self._compensate(run)
        elif action in {"resume", "recover"}:
            if run["status"] in {"cancelled", "verified", "compensated"}:
                return {"ok": False, "error": "terminal_run_cannot_resume", "run": run}
            if not prepared:
                return {"ok": False, "error": "prepared_route_required_for_recovery", "run": run}
            manifest = dict(prepared.get("manifest") or {})
            if manifest.get("manifest_hash") != run.get("manifest_hash"):
                return {"ok": False, "error": "manifest_changed_since_review", "run": run}
            run["status"] = "running"
            run["attempt"] = int(run.get("attempt") or 1) + 1
            self._event(run, "run_recovered" if action == "recover" else "run_resumed")
            self.repository.save(run)
            return self._continue(run, manifest=manifest, inputs={})
        self.repository.save(run)
        return {"ok": True, "run": run, "receipt": self._receipt(run)}

    def recover_interrupted(self, *, workspace_id: str | None = None) -> Dict[str, Any]:
        recovered = []
        for run in self.repository.list(limit=500):
            if workspace_id and str((run.get("authority_context") or {}).get("workspace_id") or "") != str(workspace_id):
                continue
            if run.get("status") == "running":
                run["status"] = "waiting"
                for node in run.get("nodes") or []:
                    if node.get("status") == "running":
                        node["status"] = "queued"
                self._event(run, "mother_restart_detected")
                self.repository.save(run)
                recovered.append(run["run_id"])
        return {"ok": True, "recovered_run_ids": recovered, "count": len(recovered)}

    def _continue(self, run: Dict[str, Any], *, manifest: Mapping[str, Any], inputs: Mapping[str, Any]) -> Dict[str, Any]:
        node_by_id = {str(node.get("id")): node for node in manifest.get("nodes") or []}
        for state in run.get("nodes") or []:
            if state["status"] == "verified":
                continue
            node = node_by_id.get(state["node_id"], {})
            state["status"] = "running"
            state["started_at"] = utc_now_iso()
            self.repository.save(run)
            try:
                if node.get("type") == "approval":
                    state["status"] = "verified"
                    state["output"] = {"approval": "validated_by_preflight"}
                elif node.get("type") == "capability":
                    key = str(node.get("idempotency_key") or f"{run['run_id']}:{state['node_id']}")
                    if self._idempotency_seen(run, key):
                        state["status"] = "verified"
                        state["output"] = {"duplicate_prevented": True, "idempotency_key": key}
                    else:
                        max_attempts = max(1, min(int(node.get("max_attempts") or 1), 5))
                        timeout_seconds = max(1, min(int(node.get("timeout_seconds") or 60), 600))
                        result: Dict[str, Any] = {}
                        for attempt in range(1, max_attempts + 1):
                            state["attempts"] = attempt
                            started = self.clock()
                            execution_inputs = {
                                **dict(inputs),
                                "_aion_workspace_id": str((run.get("authority_context") or {}).get("workspace_id") or ""),
                                "_aion_person_id": str((run.get("authority_context") or {}).get("person_id") or ""),
                                "_aion_workflow_id": str(run.get("flow_id") or ""),
                            }
                            result = dict(self.capability_executor(
                                node=node,
                                inputs=execution_inputs,
                                idempotency_key=key,
                                execution_mode=str(run.get("execution_mode") or "connector_ready"),
                            ))
                            elapsed = max(0.0, self.clock() - started)
                            if elapsed > timeout_seconds:
                                result = {"ok": False, "verified": False, "error": "capability_timeout", "elapsed_seconds": elapsed}
                            if result.get("ok") and result.get("verified"):
                                break
                            if result.get("waiting") is True:
                                break
                            if result.get("circuit_open") is True:
                                break
                            if attempt < max_attempts:
                                self._event(run, "node_retry_queued", node_id=state["node_id"], attempt=attempt + 1)
                        state["output"] = _redact(result)
                        if result.get("waiting") is True:
                            state["status"] = "waiting"
                            state["finished_at"] = None
                            run["status"] = "waiting"
                            self._event(
                                run,
                                "node_waiting_for_department_computer",
                                node_id=state["node_id"],
                                workflow_skill_run_id=result.get("workflow_skill_run_id"),
                            )
                            receipt = self._receipt(run)
                            run["receipt"] = receipt
                            self.repository.save(run)
                            return {
                                "ok": True,
                                "waiting": True,
                                "run": run,
                                "receipt": receipt,
                            }
                        state["status"] = "verified" if result.get("ok") and result.get("verified") else "failed"
                        state["idempotency_key"] = key
                        if result.get("compensation"):
                            run["compensations"].append(result["compensation"])
                        if state["status"] == "failed":
                            raise RuntimeError(str(result.get("error") or "capability_not_verified"))
                else:
                    state["status"] = "verified"
                    state["output"] = {"simulated_or_local": True, "output_hash": canonical_hash({"node": node, "inputs": _redact(dict(inputs))})}
                state["finished_at"] = utc_now_iso()
                self._event(run, "node_verified", node_id=state["node_id"])
            except Exception as exc:
                state["status"] = "failed"
                state["error"] = f"{type(exc).__name__}: {exc}"
                run["status"] = "failed"
                self._event(run, "node_failed", node_id=state["node_id"])
                self._compensate(run)
                self.repository.save(run)
                receipt = self._receipt(run)
                run["receipt"] = receipt
                self.repository.save(run)
                return {"ok": False, "run": run, "receipt": receipt}
        run["status"] = "verified"
        run["updated_at"] = utc_now_iso()
        self._event(run, "run_verified")
        receipt = self._receipt(run)
        run["receipt"] = receipt
        self.repository.save(run)
        return {"ok": True, "run": run, "receipt": receipt}

    @staticmethod
    def _normalize_graph(graph: Mapping[str, Any]) -> Dict[str, Any]:
        flow_id = str(graph.get("flow_id") or graph.get("workflow_id") or "aion-flow")
        nodes = []
        for index, raw in enumerate(graph.get("nodes") or []):
            data = dict(raw.get("data") or {})
            config = dict(raw.get("config") or data.get("config") or {})
            kind = str(raw.get("type") or data.get("kind") or config.get("kind") or "").strip()
            aliases = {"verification": "verification", "action": "capability", "ai_action": "model"}
            node = {**data, **config, **dict(raw), "id": str(raw.get("id") or data.get("step_id") or f"node_{index+1}"), "type": aliases.get(kind, kind)}
            node.pop("data", None)
            node.pop("config", None)
            if node["type"] == "model":
                node.setdefault("authorities", [])
            if node["type"] == "approval":
                node["requires_approval"] = True
                node.setdefault("approval_id", f"approval_{node['id']}")
                if not node.get("approval_id"):
                    node["approval_id"] = f"approval_{node['id']}"
                if not node.get("exact_scope_hash"):
                    node["exact_scope_hash"] = canonical_hash({"flow_id": flow_id, "node_id": node["id"], "action_id": node.get("action_id")})
            nodes.append(node)
        edges = []
        for index, raw in enumerate(graph.get("edges") or []):
            edge = dict(raw)
            edge["id"] = str(edge.get("id") or f"edge_{index+1}")
            edge["source"] = str(edge.get("source") or edge.get("from") or "")
            edge["target"] = str(edge.get("target") or edge.get("to") or "")
            edges.append(edge)
        return {"flow_id": flow_id, "nodes": nodes, "edges": edges}

    @staticmethod
    def _static_validate(manifest: Mapping[str, Any]) -> Dict[str, Any]:
        errors = []
        for node in manifest.get("nodes") or []:
            if node.get("type") == "capability" and not (node.get("capability_id") or node.get("action_id")):
                errors.append(f"capability_binding_required:{node['id']}")
            if node.get("type") == "verification" and not (node.get("expected_outcome") or node.get("rule_ref")):
                errors.append(f"verification_rule_required:{node['id']}")
        node_ids = {str(node.get("id")) for node in manifest.get("nodes") or []}
        incoming = {node_id: 0 for node_id in node_ids}
        outgoing = {node_id: [] for node_id in node_ids}
        for edge in manifest.get("edges") or []:
            source, target = str(edge.get("source")), str(edge.get("target"))
            if source in node_ids and target in node_ids:
                incoming[target] += 1
                outgoing[source].append(target)
        queue = [node_id for node_id, count in incoming.items() if count == 0]
        visited = 0
        while queue:
            current = queue.pop()
            visited += 1
            for target in outgoing[current]:
                incoming[target] -= 1
                if incoming[target] == 0:
                    queue.append(target)
        if visited != len(node_ids):
            errors.append("unbounded_graph_cycle_not_allowed")
        return {"ok": not errors, "errors": errors, "node_count": len(manifest.get("nodes") or []), "edge_count": len(manifest.get("edges") or [])}

    @staticmethod
    def _to_capsule(manifest: Mapping[str, Any]) -> Dict[str, Any]:
        ordered = AionFlowExecutionService._ordered_nodes(manifest)
        return {
            "schema_version": "aion.workflow_capsule.v1",
            "canonical_key": f"AF-{canonical_hash({'flow_id': manifest.get('flow_id'), 'hash': manifest.get('manifest_hash')})[:12]}",
            "display_name": str(manifest.get("flow_id") or "AION Flow"),
            "meaning": "Sovereign intelligence route compiled from the visible Glyph canvas.",
            "workflow_id": manifest.get("flow_id"),
            "policy": {"dry_run_first": True, "approval_before_external_write": True, "external_writes_allowed": False},
            "workflow_graph": {"nodes": list(manifest.get("nodes") or []), "edges": list(manifest.get("edges") or [])},
            "compiled_glyph": {"op": "sequence", "steps": [{"step_id": node["id"], "kind": node["type"], "raw": node} for node in ordered]},
            "meta": {"sovereign_manifest_hash": manifest.get("manifest_hash"), "compiled_not_executed": True},
        }

    @staticmethod
    def _simulate(manifest: Mapping[str, Any], inputs: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "schema_version": "aion.flow.simulation.v1",
            "status": "simulated",
            "external_writes_performed": 0,
            "nodes": [{"node_id": node["id"], "status": "simulated", "sample_output_hash": canonical_hash({"node": node["id"], "inputs": _redact(dict(inputs))})} for node in AionFlowExecutionService._ordered_nodes(manifest)],
        }

    @staticmethod
    def _disclosure_report(manifest: Mapping[str, Any], governance: Mapping[str, Any]) -> Dict[str, Any]:
        crossings = [edge for edge in governance.get("edges") or [] if edge.get("location") in {"customer_cloud", "external_api"}]
        report = {
            "schema_version": "aion.flow.predicted_disclosure_cost.v1",
            "boundary_crossings": crossings,
            "estimated_cost": sum(float(node.get("estimated_cost") or 0) for node in manifest.get("nodes") or []),
            "consequential_capabilities": sum(1 for node in manifest.get("nodes") or [] if node.get("type") == "capability" and (node.get("consequential") or node.get("causes_external_effect"))),
        }
        report["report_hash"] = canonical_hash(report)
        return report

    @staticmethod
    def _ordered_nodes(manifest: Mapping[str, Any]) -> list[Dict[str, Any]]:
        nodes = {str(node["id"]): dict(node) for node in manifest.get("nodes") or []}
        incoming = {node_id: 0 for node_id in nodes}
        outgoing = {node_id: [] for node_id in nodes}
        for edge in manifest.get("edges") or []:
            source, target = str(edge.get("source")), str(edge.get("target"))
            if source in nodes and target in nodes:
                outgoing[source].append(target)
                incoming[target] += 1
        queue = sorted(node_id for node_id, count in incoming.items() if count == 0)
        ordered = []
        while queue:
            current = queue.pop(0)
            ordered.append(nodes[current])
            for target in sorted(outgoing[current]):
                incoming[target] -= 1
                if incoming[target] == 0:
                    queue.append(target)
        return ordered + [nodes[node_id] for node_id in sorted(nodes) if node_id not in {node["id"] for node in ordered}]

    @staticmethod
    def _node_state(node: Mapping[str, Any], index: int) -> Dict[str, Any]:
        return {
            "node_id": node["id"],
            "kind": node.get("type"),
            "sequence": index + 1,
            "status": "queued",
            "attempts": 0,
            "consequential": bool(node.get("consequential") or node.get("causes_external_effect")),
        }

    @staticmethod
    def _idempotency_seen(run: Mapping[str, Any], key: str) -> bool:
        return any(node.get("idempotency_key") == key and node.get("status") == "verified" for node in run.get("nodes") or [])

    def _compensate(self, run: Dict[str, Any]) -> None:
        for compensation in reversed(run.get("compensations") or []):
            if compensation.get("status") not in {"completed", "verified"}:
                if compensation.get("safe_local") is True:
                    compensation["status"] = "completed"
                    compensation["completed_at"] = utc_now_iso()
                else:
                    compensation["status"] = "waiting_approval"
        if run.get("compensations"):
            self._event(
                run,
                "compensation_reviewed",
                pending=sum(1 for item in run["compensations"] if item.get("status") == "waiting_approval"),
            )

    def _default_capability_executor(
        self,
        *,
        node: Mapping[str, Any],
        inputs: Mapping[str, Any],
        idempotency_key: str,
        execution_mode: str = "connector_ready",
    ) -> Mapping[str, Any]:
        connector = str(node.get("connector") or node.get("target") or "").strip().lower()
        action = str(node.get("capability_id") or node.get("action_id") or "").strip().lower()
        if action == "pilot.demonstrated_skill.execute":
            from backend.modules.aion_business.runtime.pilot_operating_team_service import (
                PilotOperatingTeamService,
            )

            workspace_id = str(inputs.get("_aion_workspace_id") or "").strip()
            if not workspace_id:
                return {
                    "ok": False,
                    "verified": False,
                    "error": "workflow_skill_workspace_required",
                    "external_effect_performed": False,
                }
            try:
                return PilotOperatingTeamService().queue_workflow_skill_run(
                    workspace_id,
                    skill_id=str(node.get("skill_id") or ""),
                    skill_hash=str(node.get("skill_hash") or ""),
                    workflow_id=str(inputs.get("_aion_workflow_id") or node.get("workflow_id") or "aion-flow"),
                    workflow_node_id=str(node.get("id") or ""),
                    inputs=dict(inputs),
                    idempotency_key=idempotency_key,
                    requested_by=str(inputs.get("_aion_person_id") or "workflow:aion-flow"),
                )
            except (FileNotFoundError, PermissionError, ValueError) as exc:
                return {
                    "ok": False,
                    "verified": False,
                    "error": str(exc),
                    "external_effect_performed": False,
                }
        if connector == "gmail":
            step = {**dict(node), "output_ref": f"{node.get('id')}.output"}
            available = list(inputs.get("available_vault_requirements") or [])
            if any(marker in action for marker in ("read", "get", "search", "watch")):
                result = self.workflow_connector_adapter.read(
                    connector="gmail", step=step, inputs=dict(inputs), available_vault_requirements=available
                ).to_dict()
                return {**result, "verified": bool(result.get("ok")), "external_effect_performed": False}
            if "create_draft" in action or "draft.create" in action:
                result = self.workflow_connector_adapter.create_draft(
                    connector="gmail",
                    step=step,
                    inputs=dict(inputs),
                    approval={"status": "approved"},
                    available_vault_requirements=available,
                    execution_mode=execution_mode,
                ).to_dict()
                return {
                    **result,
                    "verified": bool(result.get("ok")),
                    "external_effect_performed": bool(result.get("ok") and execution_mode == "live_execute"),
                }
            result = self.workflow_connector_adapter.external_write_ready(
                connector="gmail",
                step=step,
                approval={"status": "approved"},
                available_vault_requirements=available,
                execution_mode=execution_mode,
            ).to_dict()
            return {**result, "verified": bool(result.get("ok")), "external_effect_performed": False}
        if node.get("consequential") or node.get("causes_external_effect"):
            return {"ok": False, "verified": False, "external_effect_performed": False, "error": "permissioned_connector_not_bound"}
        return {"ok": True, "verified": True, "mode": "read_only", "idempotency_key": idempotency_key, "output_hash": canonical_hash(_redact(dict(inputs)))}

    def _event(self, run: Dict[str, Any], event: str, **extra: Any) -> None:
        now = utc_now_iso()
        run["updated_at"] = now
        run.setdefault("events", []).append({"event": event, "at": now, **extra})

    @staticmethod
    def _receipt(run: Mapping[str, Any]) -> Dict[str, Any]:
        payload = {
            "schema_version": "aion.intelligence_route_receipt.v1",
            "receipt_id": f"receipt_{run['run_id']}",
            "run_id": run["run_id"],
            "flow_id": run.get("flow_id"),
            "manifest_hash": run.get("manifest_hash"),
            "review_hash": run.get("review_hash"),
            "status": run.get("status"),
            "node_states": [{"node_id": node.get("node_id"), "status": node.get("status"), "output_hash": canonical_hash(node.get("output") or {})} for node in run.get("nodes") or []],
            "external_effects_verified": all(
                node.get("status") == "verified"
                and (not node.get("consequential") or bool((node.get("output") or {}).get("external_effect_performed")))
                for node in run.get("nodes") or []
            ) and run.get("status") == "verified",
            "issued_at": utc_now_iso(),
        }
        payload["receipt_hash"] = canonical_hash(payload)
        return payload


def _safe_id(value: str) -> str:
    clean = "".join(character for character in str(value) if character.isalnum() or character in {"-", "_"})
    if not clean:
        raise ValueError("run_id_required")
    return clean


def _redact(value: Any) -> Any:
    secret_keys = {"password", "secret", "token", "api_key", "private_key", "authorization_header", "bearer", "credential"}
    if isinstance(value, dict):
        return {key: "[REDACTED]" if any(marker in str(key).lower() for marker in secret_keys) else _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value
