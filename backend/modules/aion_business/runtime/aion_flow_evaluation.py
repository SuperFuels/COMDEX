from __future__ import annotations

import json
import os
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Dict, Mapping

from backend.modules.aion_business.runtime.aion_flow_model_bindings import AionFlowModelBindings
from backend.modules.aion_fabric.canonical import canonical_hash, utc_now_iso


STACK_KINDS = {"model", "harness", "compute"}
METRICS = ("quality", "correctness", "evidence_coverage", "latency_ms", "cost", "energy_wh")


class AionFlowEvaluationService:
    """Customer-owned champion/challenger evidence and reversible routing decisions."""

    def __init__(self, root: str | Path = ".runtime/aion_flow/evaluations") -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        *,
        graph: Mapping[str, Any],
        node_id: str,
        challenger_value: str,
        evidence_pack: Mapping[str, Any],
        measure_scope: str = "customer_private",
        traffic_fraction: float = 0.1,
        minimum_samples: int = 3,
        authority_context: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if measure_scope not in {"customer_private", "public_benchmark"}:
            raise ValueError("evaluation_measure_scope_invalid")
        traffic = float(traffic_fraction)
        if traffic <= 0 or traffic > 0.5:
            raise ValueError("challenger_traffic_must_be_between_zero_and_half")
        nodes = list(graph.get("nodes") or [])
        selected = next((item for item in nodes if str(item.get("id")) == str(node_id)), None)
        if not selected:
            raise ValueError("comparison_node_not_found")
        kind = self._kind(selected)
        if kind not in STACK_KINDS:
            raise ValueError("only_model_harness_or_compute_nodes_can_be_swapped")
        field = {"model": "model_manifest_id", "harness": "harness_manifest_id", "compute": "target"}[kind]
        if not str(challenger_value or "").strip():
            raise ValueError("challenger_value_required")

        champion_graph = AionFlowModelBindings.redact_for_canvas(deepcopy(dict(graph)))
        challenger_graph = deepcopy(champion_graph)
        challenger = next(item for item in challenger_graph["nodes"] if str(item.get("id")) == str(node_id))
        config = dict(challenger.get("config") or {})
        settings = dict(config.get("intelligence_settings") or {})
        previous = settings.get(field, config.get(field, challenger.get(field, "")))
        settings[field] = str(challenger_value).strip()
        config["intelligence_settings"] = settings
        config[field] = str(challenger_value).strip()
        challenger["config"] = config
        challenger[field] = str(challenger_value).strip()

        safe_pack = AionFlowModelBindings.redact_for_canvas(dict(evidence_pack or {}))
        experiment_id = f"afexp_{uuid.uuid4().hex}"
        now = utc_now_iso()
        experiment = {
            "schema_version": "aion.flow.evaluation.v1",
            "experiment_id": experiment_id,
            "status": "collecting",
            "created_at": now,
            "updated_at": now,
            "measure_scope": measure_scope,
            "private_measures_exported": False,
            "evidence_pack": safe_pack,
            "evidence_pack_hash": canonical_hash(safe_pack),
            "swap": {"node_id": str(node_id), "kind": kind, "field": field, "champion_value": previous, "challenger_value": str(challenger_value).strip()},
            "traffic": {"champion": 1.0 - traffic, "challenger": traffic, "bounded": True},
            "minimum_samples": max(1, min(int(minimum_samples), 10000)),
            "variants": {
                "champion": {"graph": champion_graph, "graph_hash": canonical_hash(champion_graph), "results": []},
                "challenger": {"graph": challenger_graph, "graph_hash": canonical_hash(challenger_graph), "results": []},
            },
            "routing": {"active": "champion", "history": []},
            "drift": {"detected": False, "reasons": []},
            "learning": {"accepted_evidence_count": 0, "ignored_unverified_count": 0},
            "simulations": [],
            "authority_context": {
                key: str((authority_context or {}).get(key) or "")
                for key in ("person_id", "workspace_id", "organisation_id")
            },
        }
        return self._save(experiment)

    def run_same_pack(
        self,
        experiment_id: str,
        *,
        runner: Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]],
    ) -> Dict[str, Any]:
        """Run both immutable variants with one pack; simulation cannot teach routing."""

        item = self.get(experiment_id)
        batch_id = f"afbatch_{uuid.uuid4().hex}"
        rows = []
        for variant in ("champion", "challenger"):
            outcome = AionFlowModelBindings.redact_for_canvas(
                dict(runner(item["variants"][variant]["graph"], item["evidence_pack"]) or {})
            )
            row = {
                "variant": variant,
                "ok": outcome.get("ok") is True,
                "phase": str(outcome.get("phase") or "simulation"),
                "metrics": self._metrics(outcome.get("metrics") or {}),
                "result_hash": canonical_hash(outcome),
                "accepted_for_learning": False,
            }
            rows.append(row)
        item.setdefault("simulations", []).append({
            "batch_id": batch_id,
            "at": utc_now_iso(),
            "evidence_pack_hash": item["evidence_pack_hash"],
            "same_pack_verified": True,
            "external_writes": 0,
            "results": rows,
        })
        item["updated_at"] = utc_now_iso()
        return self._save(item)

    def record(self, experiment_id: str, *, variant: str, result: Mapping[str, Any]) -> Dict[str, Any]:
        item = self.get(experiment_id)
        if variant not in {"champion", "challenger"}:
            raise ValueError("evaluation_variant_invalid")
        if str(result.get("evidence_pack_hash") or "") != item["evidence_pack_hash"]:
            raise ValueError("same_versioned_evidence_pack_required")
        accepted = bool(result.get("verified_outcome") is True or result.get("human_correction") is True)
        safe = AionFlowModelBindings.redact_for_canvas(dict(result))
        row = {
            "recorded_at": utc_now_iso(),
            "accepted_for_learning": accepted,
            "source": "verified_outcome" if result.get("verified_outcome") is True else ("human_correction" if result.get("human_correction") is True else "unverified"),
            "metrics": self._metrics(safe.get("metrics") or {}),
            "provider_fingerprint": str(safe.get("provider_fingerprint") or "")[:200],
            "receipt_ref": str(safe.get("receipt_ref") or "")[:300],
        }
        item["variants"][variant]["results"].append(row)
        key = "accepted_evidence_count" if accepted else "ignored_unverified_count"
        item["learning"][key] += 1
        item["updated_at"] = utc_now_iso()
        self._refresh(item)
        return self._save(item)

    def promote(self, experiment_id: str, *, actor_id: str, reason: str) -> Dict[str, Any]:
        item = self.get(experiment_id)
        comparison = self._comparison(item)
        if not comparison["challenger_eligible"]:
            raise PermissionError("challenger_not_eligible_for_promotion")
        previous = item["routing"]["active"]
        decision = {
            "at": utc_now_iso(), "actor_id": str(actor_id)[:160], "from": previous, "to": "challenger",
            "reason": str(reason or "Measured verified outcome improvement")[:500],
            "comparison_hash": comparison["comparison_hash"],
        }
        decision["decision_hash"] = canonical_hash(decision)
        item["routing"]["history"].append(decision)
        item["routing"]["active"] = "challenger"
        item["status"] = "challenger_promoted"
        item["updated_at"] = utc_now_iso()
        return self._save(item)

    def reverse(self, experiment_id: str, *, actor_id: str, reason: str) -> Dict[str, Any]:
        item = self.get(experiment_id)
        previous = item["routing"]["active"]
        decision = {"at": utc_now_iso(), "actor_id": str(actor_id)[:160], "from": previous, "to": "champion", "reason": str(reason or "Manual rollback")[:500]}
        decision["decision_hash"] = canonical_hash(decision)
        item["routing"]["history"].append(decision)
        item["routing"]["active"] = "champion"
        item["status"] = "rolled_back"
        item["updated_at"] = utc_now_iso()
        return self._save(item)

    def get(self, experiment_id: str) -> Dict[str, Any]:
        path = self.root / f"{self._safe_id(experiment_id)}.json"
        if not path.exists():
            raise KeyError("evaluation_not_found")
        value = json.loads(path.read_text(encoding="utf-8"))
        value["comparison"] = self._comparison(value)
        return value

    def list(self, limit: int = 25, *, workspace_id: str | None = None) -> Dict[str, Any]:
        items = []
        for path in sorted(self.root.glob("*.json"), key=lambda value: value.stat().st_mtime, reverse=True)[: max(1, min(limit, 100))]:
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if workspace_id and str((value.get("authority_context") or {}).get("workspace_id") or "") != str(workspace_id):
                    continue
                items.append({key: value.get(key) for key in ("experiment_id", "status", "created_at", "updated_at", "measure_scope", "swap", "routing", "drift")} | {"comparison": self._comparison(value)})
            except (OSError, json.JSONDecodeError):
                continue
        return {"schema_version": "aion.flow.evaluation.list.v1", "experiments": items}

    def _refresh(self, item: Dict[str, Any]) -> None:
        baseline = [row for row in item["variants"]["champion"]["results"] if row["accepted_for_learning"]]
        recent = [row for row in item["variants"]["challenger"]["results"] if row["accepted_for_learning"]]
        reasons = []
        if baseline and recent:
            base = self._average(baseline)
            challenger = self._average(recent)
            if challenger["correctness"] + 0.05 < base["correctness"]:
                reasons.append("correctness_regression")
            if challenger["evidence_coverage"] + 0.1 < base["evidence_coverage"]:
                reasons.append("evidence_coverage_regression")
            fingerprints = {row.get("provider_fingerprint") for row in recent if row.get("provider_fingerprint")}
            if len(fingerprints) > 1:
                reasons.append("provider_behavior_fingerprint_changed")
        item["drift"] = {"detected": bool(reasons), "reasons": reasons, "checked_at": utc_now_iso()}

    def _comparison(self, item: Mapping[str, Any]) -> Dict[str, Any]:
        accepted = {
            name: [row for row in (item.get("variants", {}).get(name, {}).get("results") or []) if row.get("accepted_for_learning")]
            for name in ("champion", "challenger")
        }
        averages = {name: self._average(rows) for name, rows in accepted.items()}
        minimum = int(item.get("minimum_samples") or 1)
        enough = all(len(rows) >= minimum for rows in accepted.values())
        c, h = averages["champion"], averages["challenger"]
        better = h["quality"] > c["quality"] and h["correctness"] >= c["correctness"] and h["evidence_coverage"] >= c["evidence_coverage"]
        result = {
            "sample_counts": {name: len(rows) for name, rows in accepted.items()},
            "averages": averages,
            "minimum_samples_met": enough,
            "challenger_eligible": bool(enough and better and not item.get("drift", {}).get("detected")),
            "recommendation": "promote_challenger" if enough and better and not item.get("drift", {}).get("detected") else "retain_champion",
            "learning_basis": "verified_outcomes_and_explicit_corrections_only",
            "measure_scope": item.get("measure_scope"),
        }
        result["comparison_hash"] = canonical_hash(result)
        return result

    @staticmethod
    def _kind(node: Mapping[str, Any]) -> str:
        text = " ".join(str(value) for value in (node.get("type"), node.get("kind"), node.get("config", {}).get("kind"), node.get("config", {}).get("module_id"))).lower()
        if "harness" in text:
            return "harness"
        if "compute" in text:
            return "compute"
        if "model" in text:
            return "model"
        return ""

    @staticmethod
    def _metrics(value: Mapping[str, Any]) -> Dict[str, float]:
        clean = {}
        for name in METRICS:
            number = float(value.get(name) or 0)
            if name in {"quality", "correctness", "evidence_coverage"}:
                number = max(0.0, min(number, 1.0))
            else:
                number = max(0.0, number)
            clean[name] = number
        return clean

    @staticmethod
    def _average(rows: list[Mapping[str, Any]]) -> Dict[str, float]:
        if not rows:
            return {name: 0.0 for name in METRICS}
        return {name: round(sum(float(row.get("metrics", {}).get(name) or 0) for row in rows) / len(rows), 6) for name in METRICS}

    @staticmethod
    def _safe_id(value: str) -> str:
        clean = str(value or "")
        if not clean.startswith("afexp_") or not clean.replace("_", "").isalnum():
            raise ValueError("evaluation_id_invalid")
        return clean

    def _save(self, item: Mapping[str, Any]) -> Dict[str, Any]:
        safe = AionFlowModelBindings.redact_for_canvas(dict(item))
        safe.pop("comparison", None)
        path = self.root / f"{self._safe_id(str(safe['experiment_id']))}.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(safe, indent=2, sort_keys=True), encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        safe["comparison"] = self._comparison(safe)
        return safe
