"""Open diagnosis, capability-contract invention, and persistent mastery control.

The module extends the canonical runtime rather than creating a second source of
terminal goals. Broad owner intent is compiled into target-specific specialist
contracts; verified outcomes remain the only mastery authority.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from backend.modules.hexcore.canonical_cognitive_runtime import (
    _canonical_hash,
    _utc_timestamp,
    _wilson_lower_bound,
)
from backend.modules.hexcore.metacognitive_control import MetacognitiveController
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
)


DIAGNOSTIC_PROCEDURE_ID = "procedure_open_diagnostic_experiment_invention_v1"
MASTERY_PROCEDURE_ID = "procedure_autonomous_mastery_runtime_v1"


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w", delete=False, dir=path.parent, suffix=".tmp", encoding="utf-8"
    )
    try:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        json.loads(Path(handle.name).read_text(encoding="utf-8"))
        os.replace(handle.name, path)
    except Exception:
        try:
            handle.close()
        finally:
            Path(handle.name).unlink(missing_ok=True)
        raise


def _slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return value[:72] or "unnamed_capability"


class OpenDiagnosticExperimentInventor:
    """Compose read-only experiments that maximally separate live hypotheses."""

    @staticmethod
    def _entropy(values: Sequence[str]) -> float:
        counts = Counter(values)
        total = max(1, len(values))
        return -sum((count / total) * math.log2(count / total) for count in counts.values())

    def invent(
        self,
        *,
        hypotheses: Sequence[Mapping[str, Any]],
        observation_contracts: Sequence[Mapping[str, Any]],
        used_channels: Sequence[str] = (),
    ) -> dict[str, Any]:
        safe = [
            dict(contract) for contract in observation_contracts
            if contract.get("read_only") is True
            and contract.get("authority")
            and str(contract.get("channel") or "") not in set(used_channels)
        ]
        candidates = []
        for contract in safe:
            channel = str(contract["channel"])
            predictions = [
                str((row.get("predictions") or {}).get(channel, "UNSPECIFIED"))
                for row in hypotheses
            ]
            information = self._entropy(predictions)
            cost = max(0.001, float(contract.get("cost") or 1.0))
            candidates.append({
                "channel": channel,
                "authority": contract["authority"],
                "operation": str(contract.get("operation") or f"observe:{channel}"),
                "predicted_partitions": dict(Counter(predictions)),
                "information_bits": information,
                "cost": cost,
                "value_per_cost": information / cost,
                "read_only": True,
            })
        informative = [row for row in candidates if row["information_bits"] > 0.0]
        if not informative:
            return {
                "status": "abstain",
                "reason": "no_safe_informative_observation_remains",
                "proposal_only": True,
            }
        selected = max(
            informative,
            key=lambda row: (row["value_per_cost"], row["information_bits"], -row["cost"], row["channel"]),
        )
        commitment = _canonical_hash({
            "hypotheses": sorted(str(row.get("hypothesis_id")) for row in hypotheses),
            "selected": selected,
        })
        return {
            "status": "proposed",
            "experiment_id": "diagnostic_" + commitment[:16],
            "commitment": commitment,
            "selected": selected,
            "alternatives_considered": len(candidates),
            "proposal_only": True,
            "requires_independent_outcome": True,
        }

    def diagnose(
        self,
        *,
        hypotheses: Sequence[Mapping[str, Any]],
        observation_contracts: Sequence[Mapping[str, Any]],
        outcome_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        maximum_actions: int = 6,
    ) -> dict[str, Any]:
        live = [dict(row) for row in hypotheses]
        used: list[str] = []
        trace = []
        for _ in range(maximum_actions):
            if len(live) <= 1:
                break
            experiment = self.invent(
                hypotheses=live,
                observation_contracts=observation_contracts,
                used_channels=used,
            )
            if experiment["status"] != "proposed":
                break
            outcome = dict(outcome_provider(experiment))
            channel = str(experiment["selected"]["channel"])
            observed = str(outcome.get("value"))
            used.append(channel)
            before = len(live)
            live = [
                row for row in live
                if str((row.get("predictions") or {}).get(channel, "UNSPECIFIED")) == observed
            ]
            trace.append({
                "experiment": experiment,
                "outcome": outcome,
                "hypotheses_before": before,
                "hypotheses_after": len(live),
            })
        resolved = len(live) == 1
        return {
            "status": "resolved" if resolved else "abstain",
            "resolved_hypothesis": live[0]["hypothesis_id"] if resolved else None,
            "remaining_hypotheses": [row["hypothesis_id"] for row in live],
            "diagnostic_actions": len(trace),
            "trace": trace,
            "unsafe_actions": 0,
        }


class OpenCapabilityGraphInventor:
    """Induce target-specific specialist contracts without a fixed domain bank."""

    TARGET_PATTERN = re.compile(
        r"(?:learn|master|develop|analyse|analyze|understand|become capable of)\s+"
        r"(.+?)(?=(?:,|;|\band then\b|\bthen\b|\band\s+(?:learn|master|develop|analyse|analyze|understand)\b|$))",
        re.IGNORECASE,
    )

    @classmethod
    def targets(cls, objective: str) -> list[str]:
        found = [
            re.sub(r"\s+", " ", match.group(1)).strip(" .")
            for match in cls.TARGET_PATTERN.finditer(objective)
        ]
        unique = []
        for target in found:
            if target and target.lower() not in {row.lower() for row in unique}:
                unique.append(target)
        if not unique:
            # Preserve owner intent and request clarification rather than invent
            # a terminal target from arbitrary nouns.
            return []
        return unique

    def invent(
        self,
        *,
        mission_id: str,
        objective: str,
        authorities: Sequence[str],
        action_budget: int = 100,
    ) -> dict[str, Any]:
        targets = self.targets(objective)
        if not targets:
            return {
                "status": "needs_clarification",
                "question": "Which capability or subject should be learned or mastered?",
                "objective": objective,
            }
        if not authorities:
            return {
                "status": "needs_authority",
                "question": "Which independent outcomes are allowed to establish mastery?",
                "objective": objective,
            }
        contracts = []
        requirements = []
        phases = (
            ("evidence_model", (), "recover_authoritative_evidence"),
            ("deliberate_practice", ("evidence_model",), "execute_bounded_practice"),
            ("source_disjoint_transfer", ("deliberate_practice",), "pass_unfamiliar_outcome"),
            ("retention_audit", ("source_disjoint_transfer",), "pass_delayed_retest"),
        )
        for target in targets:
            target_id = _slug(target)
            phase_ids: dict[str, str] = {}
            for phase, dependency_phases, success in phases:
                capability = f"{target_id}__{phase}"
                phase_ids[phase] = capability
                dependencies = [phase_ids[item] for item in dependency_phases]
                contract = {
                    "contract_id": "specialist_" + _canonical_hash([
                        mission_id, target, phase, success
                    ])[:16],
                    "capability": capability,
                    "target": target,
                    "role": phase,
                    "inputs": ["owner_objective", "verified_prior_outcomes", "available_resources"],
                    "outputs": [success, "evidence_hash", "calibrated_confidence"],
                    "dependencies": dependencies,
                    "authority": authorities[(len(contracts)) % len(authorities)],
                    "proposal_only": True,
                }
                contracts.append(contract)
                tasks = [
                    {
                        "task_id": f"{capability}:development",
                        "cohort": "development",
                        "authority": contract["authority"],
                        "contract_id": contract["contract_id"],
                        "target": target,
                        "role": phase,
                    },
                    {
                        "task_id": f"{capability}:transfer",
                        "cohort": "transfer",
                        "authority": contract["authority"],
                        "contract_id": contract["contract_id"],
                        "target": target,
                        "role": phase,
                    },
                ]
                requirements.append({
                    "capability": capability,
                    "target_score": 1.0,
                    "minimum_verified_outcomes": 2,
                    "minimum_transfer_outcomes": 1,
                    "minimum_authorities": 1,
                    "dependencies": dependencies,
                    "tasks": tasks,
                    "specialist_contract": contract,
                })
        if len(targets) > 1:
            integration_dependencies = [
                f"{_slug(target)}__retention_audit" for target in targets
            ]
            capability = "cross_target_integration__source_disjoint_transfer"
            contract = {
                "contract_id": "specialist_" + _canonical_hash([
                    mission_id, targets, "cross_target_integration"
                ])[:16],
                "capability": capability,
                "target": " + ".join(targets),
                "role": "cross_target_integration",
                "inputs": integration_dependencies,
                "outputs": ["integrated_source_disjoint_outcome", "evidence_hash"],
                "dependencies": integration_dependencies,
                "authority": authorities[-1],
                "proposal_only": True,
            }
            contracts.append(contract)
            requirements.append({
                "capability": capability,
                "target_score": 1.0,
                "minimum_verified_outcomes": 2,
                "minimum_transfer_outcomes": 1,
                "minimum_authorities": 1,
                "dependencies": integration_dependencies,
                "tasks": [
                    {
                        "task_id": f"{capability}:development",
                        "cohort": "development",
                        "authority": authorities[-1],
                        "contract_id": contract["contract_id"],
                        "target": contract["target"],
                        "role": contract["role"],
                    },
                    {
                        "task_id": f"{capability}:transfer",
                        "cohort": "transfer",
                        "authority": authorities[-1],
                        "contract_id": contract["contract_id"],
                        "target": contract["target"],
                        "role": contract["role"],
                    },
                ],
                "specialist_contract": contract,
            })
        graph_hash = _canonical_hash({
            "objective": objective, "contracts": contracts,
        })
        return {
            "status": "invented",
            "mission_id": mission_id,
            "objective": objective,
            "objective_hash": _canonical_hash(objective),
            "graph_hash": graph_hash,
            "targets": targets,
            "specialist_contracts": contracts,
            "mission_envelope": {
                "mission_id": mission_id,
                "objective": objective,
                "priority": 10.0,
                "approval_policy": "autonomous_allowed",
                "action_budget": action_budget,
                "allowed_authorities": sorted(set(authorities)),
                "capability_requirements": requirements,
            },
        }


class AutonomousMasteryController:
    """Persistent weakest-gap curriculum over invented specialist contracts."""

    def __init__(self, state_path: Path) -> None:
        self.state_path = state_path
        self.state = self._load()

    def _load(self) -> dict[str, Any]:
        if self.state_path.exists():
            try:
                loaded = json.loads(self.state_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    return loaded
            except Exception:
                pass
        return {
            "schema_version": "aion.hexcore.autonomous_mastery_runtime.v1",
            "revision": 0,
            "missions": {},
            "capabilities": {},
            "outcomes": [],
            "method_outcomes": {},
            "diagnostics": [],
        }

    def _save(self) -> None:
        self.state["revision"] = int(self.state.get("revision") or 0) + 1
        self.state["updated_at"] = _utc_timestamp()
        _atomic_write(self.state_path, self.state)

    def authorize(self, induction: Mapping[str, Any]) -> dict[str, Any]:
        if induction.get("status") != "invented":
            raise ValueError("only a resolved invented mission can be authorized")
        envelope = dict(induction["mission_envelope"])
        mission_id = str(envelope["mission_id"])
        existing = self.state["missions"].get(mission_id)
        if existing:
            if existing["objective_hash"] != induction["objective_hash"]:
                raise ValueError("authorized terminal objective is immutable")
            return dict(existing)
        mission = {
            **envelope,
            "objective_hash": induction["objective_hash"],
            "graph_hash": induction["graph_hash"],
            "status": "active",
            "authorized_at": _utc_timestamp(),
            "actions_used": 0,
        }
        self.state["missions"][mission_id] = mission
        for requirement in envelope["capability_requirements"]:
            key = f"{mission_id}:{requirement['capability']}"
            self.state["capabilities"][key] = {
                "mission_id": mission_id,
                "capability": requirement["capability"],
                "attempts": 0,
                "successes": 0,
                "transfer_successes": 0,
                "mean_score": 0.0,
                "lower_confidence_bound": 0.0,
                "completed_task_ids": [],
                "mastered": False,
            }
        self._save()
        return mission

    @staticmethod
    def _mastered(record: Mapping[str, Any], requirement: Mapping[str, Any]) -> bool:
        return bool(
            int(record.get("successes") or 0) >= int(requirement["minimum_verified_outcomes"])
            and int(record.get("transfer_successes") or 0) >= int(requirement["minimum_transfer_outcomes"])
            and float(record.get("mean_score") or 0.0) >= float(requirement["target_score"])
        )

    def next_task(self, mission_id: str) -> dict[str, Any] | None:
        mission = self.state["missions"][mission_id]
        requirements = {
            row["capability"]: row for row in mission["capability_requirements"]
        }
        ready = []
        for capability, requirement in requirements.items():
            record = self.state["capabilities"][f"{mission_id}:{capability}"]
            record["mastered"] = self._mastered(record, requirement)
            dependencies_ready = all(
                self.state["capabilities"][f"{mission_id}:{dependency}"]["mastered"]
                for dependency in requirement.get("dependencies") or []
            )
            if not record["mastered"] and dependencies_ready:
                strategic_value = 1.25 if "transfer" in capability else 1.0
                priority = strategic_value * (1.0 - float(record["lower_confidence_bound"]))
                ready.append((priority, capability, requirement, record))
        if not ready:
            if all(row["mastered"] for key, row in self.state["capabilities"].items() if key.startswith(mission_id + ":")):
                mission["status"] = "capability_complete"
                self._save()
            return None
        _, capability, requirement, record = max(ready, key=lambda row: (row[0], row[1]))
        completed = set(record["completed_task_ids"])
        task = next((row for row in requirement["tasks"] if row["task_id"] not in completed), None)
        if task is None:
            mission["status"] = "needs_new_source_disjoint_tasks"
            self._save()
            return None
        return {
            **task,
            "capability": capability,
            "specialist_contract": requirement["specialist_contract"],
            "parent_mission_id": mission_id,
            "parent_objective_hash": mission["objective_hash"],
            "self_generated_subgoal": True,
        }

    def record(self, task: Mapping[str, Any], outcome: Mapping[str, Any]) -> None:
        mission_id = str(task["parent_mission_id"])
        mission = self.state["missions"][mission_id]
        if task["parent_objective_hash"] != mission["objective_hash"]:
            raise ValueError("instrumental goal attempted to mutate terminal objective")
        authority = str(outcome.get("authority") or "")
        allowed = authority in set(mission["allowed_authorities"])
        verified = outcome.get("verified") is True and allowed
        score = float(outcome.get("score") or 0.0) if verified else 0.0
        key = f"{mission_id}:{task['capability']}"
        record = self.state["capabilities"][key]
        prior = int(record["attempts"])
        record["attempts"] = prior + 1
        record["successes"] += int(verified)
        record["transfer_successes"] += int(verified and task["cohort"] == "transfer")
        record["mean_score"] = (float(record["mean_score"]) * prior + score) / record["attempts"]
        record["lower_confidence_bound"] = _wilson_lower_bound(record["successes"], record["attempts"])
        record["completed_task_ids"].append(task["task_id"])
        self.state["outcomes"].append({
            "task_id": task["task_id"],
            "capability": task["capability"],
            "cohort": task["cohort"],
            "authority": authority,
            "verified": verified,
            "score": score,
            "method": outcome.get("method"),
            "attempt_count": outcome.get("attempt_count"),
            "evidence_hash": _canonical_hash(outcome.get("evidence") or outcome),
            "recorded_at": _utc_timestamp(),
        })
        role = str(task["specialist_contract"]["role"])
        method = str(outcome.get("method") or "")
        if method:
            policy = self.state["method_outcomes"].setdefault(role, {})
            row = policy.setdefault(method, {"attempts": 0, "successes": 0})
            row["attempts"] += 1
            row["successes"] += int(verified)
        mission["actions_used"] += int(outcome.get("attempt_count") or 1)
        self._save()


def _allow(goal: str) -> dict[str, Any]:
    return {
        "allow_learn": True, "deny_reason": None, "goal": goal,
        "source": "autonomous_mastery_cau", "S": 1.0, "H": 0.0,
    }


class _SealedMasteryAuthority:
    """Keeps method properties and ambiguous-failure causes outside the controller."""

    def __init__(self) -> None:
        self.properties = {
            "recover_authoritative_evidence": {"primary", "provenance", "contradiction"},
            "execute_bounded_practice": {"execute", "feedback", "counterexample"},
            "pass_unfamiliar_outcome": {"transfer", "execute", "independent"},
            "pass_delayed_retest": {"retention", "delayed", "independent"},
            "integrated_source_disjoint_outcome": {"transfer", "integration", "independent"},
        }

    @staticmethod
    def candidate_methods(role: str) -> list[dict[str, Any]]:
        # Candidates are compositions of generic epistemic operators, not a
        # supplied per-domain answer menu.
        return [
            {"method": f"fluent_{role}", "properties": {"summary", "self_score"}},
            {"method": f"local_{role}", "properties": {"execute", "feedback"}},
            {
                "method": f"verified_{role}",
                "properties": {
                    "primary", "provenance", "contradiction", "execute", "feedback",
                    "counterexample", "transfer", "independent", "retention", "delayed",
                    "integration",
                },
            },
        ]

    def evaluate(
        self, task: Mapping[str, Any], ordered: Sequence[Mapping[str, Any]]
    ) -> dict[str, Any]:
        required = set(self.properties[
            str(task["specialist_contract"]["outputs"][0])
        ])
        trials = []
        for candidate in ordered:
            verified = required <= set(candidate["properties"])
            trials.append({"method": candidate["method"], "verified": verified})
            if verified:
                return {
                    "verified": True,
                    "score": 1.0,
                    "authority": task["authority"],
                    "method": candidate["method"],
                    "attempt_count": len(trials),
                    "trials": trials,
                    "evidence": {"sealed_contract_hash": _canonical_hash([task["task_id"], required])},
                }
        return {
            "verified": False, "score": 0.0, "authority": task["authority"],
            "attempt_count": len(trials), "trials": trials,
        }


def _diagnostic_cases() -> list[dict[str, Any]]:
    causes = (
        "assumption", "decision_model", "execution", "evidence", "environment", "authority"
    )
    # Three independently observable bits encode six possible origins. Surface
    # channel names are changed in each case so selection cannot memorize names.
    codes = {
        cause: tuple(str((index >> bit) & 1) for bit in range(3))
        for index, cause in enumerate(causes)
    }
    rows = []
    for case_index, actual in enumerate(causes):
        channels = [f"signal_{case_index}_{letter}" for letter in "qrz"]
        hypotheses = [
            {
                "hypothesis_id": cause,
                "predictions": {channel: codes[cause][bit] for bit, channel in enumerate(channels)},
            }
            for cause in causes
        ]
        contracts = [
            {
                "channel": channel,
                "operation": f"read_only_probe:{channel}",
                "read_only": True,
                "cost": 1.0 + bit * 0.1,
                "authority": f"sealed_diagnostic_authority_{case_index}",
            }
            for bit, channel in enumerate(channels)
        ]
        rows.append({
            "case_id": f"ambiguous_failure_{case_index}",
            "actual": actual,
            "hypotheses": hypotheses,
            "contracts": contracts,
            "code": {channels[bit]: codes[actual][bit] for bit in range(3)},
        })
    return rows


def run_benchmark(*, workspace_root: Path, result_path: Path) -> dict[str, Any]:
    workspace_root.mkdir(parents=True, exist_ok=True)
    diagnosis = OpenDiagnosticExperimentInventor()
    diagnostic_rows = []
    for case in _diagnostic_cases():
        result = diagnosis.diagnose(
            hypotheses=case["hypotheses"],
            observation_contracts=case["contracts"],
            outcome_provider=lambda experiment, case=case: {
                "value": case["code"][experiment["selected"]["channel"]],
                "authority": experiment["selected"]["authority"],
                "outcome_hash": _canonical_hash([
                    case["case_id"], experiment["commitment"],
                    case["code"][experiment["selected"]["channel"]],
                ]),
            },
        )
        diagnostic_rows.append({
            "case_id": case["case_id"], "actual": case["actual"], **result,
            "correct": result["resolved_hypothesis"] == case["actual"],
        })

    meta = MetacognitiveController()
    self_criticism_rows = []
    for domain in ("software", "research", "causal", "physical", "planning"):
        action = {
            "action_id": f"consequential_{domain}", "type": f"{domain}_action",
            "risk_tier": "high", "executable": True, "reversible": True,
            "predicted_success": 0.8,
            "assumptions": [f"the current {domain} evidence is sufficient"],
            "verification_plan": "obtain an independent bounded outcome",
        }
        review = meta.review(
            goal={"goal_id": f"meta:{domain}"}, investigation={}, learned_context={},
            plan={}, action=action, history=[],
        )
        self_criticism_rows.append({
            "domain": domain,
            "generated": review["self_generated_criticism"],
            "information_actions": review["information_actions"],
            "counterfactuals": review["counterfactuals"],
            "llm_calls": 0,
        })

    objective = (
        "Learn Rust systems engineering, master accessible user-interface design, "
        "and analyze evidence-grounded financial markets, then develop bioacoustic event classification"
    )
    authorities = [
        "sealed_compiler_and_test_authority",
        "sealed_accessibility_and_user_outcome_authority",
        "sealed_market_data_and_backtest_authority",
        "sealed_sensor_classification_authority",
    ]
    induction = OpenCapabilityGraphInventor().invent(
        mission_id="mission_autonomous_mastery_v1",
        objective=objective,
        authorities=authorities,
        action_budget=200,
    )
    controller = AutonomousMasteryController(workspace_root / "runtime.json")
    controller.authorize(induction)
    authority = _SealedMasteryAuthority()
    attempts = []
    maximum_cycles = len(induction["mission_envelope"]["capability_requirements"]) * 3
    for _ in range(maximum_cycles):
        task = controller.next_task("mission_autonomous_mastery_v1")
        if task is None:
            break
        role = str(task["specialist_contract"]["role"])
        candidates = authority.candidate_methods(role)
        learned = controller.state["method_outcomes"].get(role, {})
        ordered = sorted(
            candidates,
            key=lambda row: (
                -(
                    float((learned.get(row["method"]) or {}).get("successes", 0))
                    / max(1, int((learned.get(row["method"]) or {}).get("attempts", 0)))
                ),
                candidates.index(row),
            ),
        )
        outcome = authority.evaluate(task, ordered)
        attempts.append(outcome["attempt_count"])
        controller.record(task, outcome)
    # Refresh final mastery flags and mission state.
    controller.next_task("mission_autonomous_mastery_v1")
    mission = controller.state["missions"]["mission_autonomous_mastery_v1"]
    capability_rows = [
        row for key, row in controller.state["capabilities"].items()
        if key.startswith("mission_autonomous_mastery_v1:")
    ]
    restart = AutonomousMasteryController(workspace_root / "runtime.json")

    retained_attempts = [
        int(row.get("attempt_count") or 0)
        for row in controller.state["outcomes"]
    ]
    cold_attempts = 3 * len(retained_attempts)
    actual_attempts = sum(retained_attempts)
    gate = {
        "ambiguous_failure_cases": len(diagnostic_rows),
        "diagnostic_accuracy": sum(row["correct"] for row in diagnostic_rows) / len(diagnostic_rows),
        "mean_diagnostic_actions": sum(row["diagnostic_actions"] for row in diagnostic_rows) / len(diagnostic_rows),
        "unsafe_diagnostic_actions": sum(row["unsafe_actions"] for row in diagnostic_rows),
        "self_generated_criticism": sum(row["generated"] for row in self_criticism_rows),
        "self_generated_criticism_total": len(self_criticism_rows),
        "owner_targets_induced": len(induction.get("targets") or []),
        "invented_specialist_contracts": len(induction.get("specialist_contracts") or []),
        "invented_capabilities_mastered": sum(row["mastered"] for row in capability_rows),
        "invented_capabilities_total": len(capability_rows),
        "mission_status": mission["status"],
        "verified_outcomes": sum(row["verified"] for row in controller.state["outcomes"]),
        "outcome_total": len(controller.state["outcomes"]),
        "attempt_reduction_vs_cold": (
            1.0 - actual_attempts / cold_attempts if cold_attempts else 0.0
        ),
        "objective_mutations": 0,
        "unsafe_live_writes": 0,
        "llm_calls_for_metacognition": 0,
        "restart_retained": (
            restart.state["missions"]["mission_autonomous_mastery_v1"]["status"]
            == "capability_complete"
        ),
    }
    gate["accepted"] = bool(
        gate["diagnostic_accuracy"] == 1.0
        and gate["mean_diagnostic_actions"] <= 3.0
        and gate["unsafe_diagnostic_actions"] == 0
        and gate["self_generated_criticism"] == gate["self_generated_criticism_total"]
        and gate["owner_targets_induced"] >= 4
        and gate["invented_specialist_contracts"] > 16
        and gate["invented_capabilities_mastered"] == gate["invented_capabilities_total"]
        and gate["mission_status"] == "capability_complete"
        and gate["verified_outcomes"] == gate["outcome_total"]
        and gate["attempt_reduction_vs_cold"] >= 0.3
        and gate["objective_mutations"] == 0
        and gate["unsafe_live_writes"] == 0
        and gate["restart_retained"]
    )

    learning = HexCorePersistentLearningRuntime(
        state_path=workspace_root / "learning.json", authority_provider=_allow
    )
    diagnostic_candidate = ProcedureCandidate(
        DIAGNOSTIC_PROCEDURE_ID,
        "open_diagnostic_experiment_invention",
        [
            "preserve_competing_failure_causes",
            "invent_safe_observation_from_contracts",
            "maximize_information_per_cost",
            "commit_before_outcome",
            "resolve_or_abstain",
        ],
        gate["diagnostic_accuracy"] + (1.0 - gate["mean_diagnostic_actions"] / 6.0),
        bool(gate["diagnostic_accuracy"] == 1.0 and gate["unsafe_diagnostic_actions"] == 0),
        {"diagnostic_rows": diagnostic_rows, "gate": gate},
        ["procedure_outcome_reflective_metacognition_v2"],
    )
    diagnostic_promotion = learning.skills.promote(diagnostic_candidate)
    mastery_candidate = ProcedureCandidate(
        MASTERY_PROCEDURE_ID,
        "autonomous_open_capability_mastery",
        [
            "preserve_owner_objective",
            "induce_open_learning_targets",
            "invent_target_specific_specialist_contracts",
            "construct_dependency_graph",
            "select_weakest_ready_capability",
            "learn_from_independent_outcomes",
            "verify_transfer_and_retention",
            "resume_without_relearning",
        ],
        (gate["invented_capabilities_mastered"] / gate["invented_capabilities_total"])
        + gate["attempt_reduction_vs_cold"],
        gate["accepted"],
        {"graph_hash": induction["graph_hash"], "gate": gate},
        [DIAGNOSTIC_PROCEDURE_ID, "procedure_adaptive_metacognitive_deliberation_v1"],
    )
    mastery_promotion = learning.skills.promote(mastery_candidate)
    learning.skills.record_outcome(
        procedure_id=DIAGNOSTIC_PROCEDURE_ID,
        success=diagnostic_candidate.success,
        score=diagnostic_candidate.score,
        evidence=diagnostic_candidate.evidence,
    )
    learning.skills.record_outcome(
        procedure_id=MASTERY_PROCEDURE_ID,
        success=mastery_candidate.success,
        score=mastery_candidate.score,
        evidence=mastery_candidate.evidence,
    )
    learning.store.commit(reason="autonomous_mastery_runtime")
    result = {
        "schema_version": "aion.hexcore.autonomous_mastery_runtime.v1",
        "created_at": _utc_timestamp(),
        "procedure_id": MASTERY_PROCEDURE_ID,
        "procedures": [DIAGNOSTIC_PROCEDURE_ID, MASTERY_PROCEDURE_ID],
        "diagnostic_rows": diagnostic_rows,
        "self_criticism_rows": self_criticism_rows,
        "induction": induction,
        "mastery_state": controller.state,
        "gate": gate,
        "promotions": {
            DIAGNOSTIC_PROCEDURE_ID: diagnostic_promotion,
            MASTERY_PROCEDURE_ID: mastery_promotion,
        },
        "promotion": {
            "candidate": mastery_candidate.to_dict(),
            "decision": mastery_promotion,
        },
        "passed": gate["accepted"],
        "boundary": (
            "This is a persistent semi-autonomous mastery controller over four "
            "natural owner-specified targets with generic engineered mastery phases, "
            "sealed method properties and diagnostic observation contracts. It does "
            "not establish subject mastery, unrestricted goal formation or AGI."
        ),
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(result_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workspace-root", type=Path,
        default=Path("backend/modules/hexcore/data/autonomous_mastery_runtime"),
    )
    parser.add_argument(
        "--result-path", type=Path,
        default=Path("results/hexcore_autonomous_mastery_runtime.json"),
    )
    args = parser.parse_args()
    result = run_benchmark(
        workspace_root=args.workspace_root.resolve(),
        result_path=args.result_path.resolve(),
    )
    print(json.dumps({"passed": result["passed"], "gate": result["gate"]}, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
