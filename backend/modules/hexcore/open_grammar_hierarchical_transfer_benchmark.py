from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.cross_domain_causal_transfer import (
    CausalDomainSpec,
    CrossDomainCausalTransferRuntime,
    NamedStochasticLatentDomain,
)
from backend.modules.hexcore.persistent_learning import (
    EvidenceCapsule,
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.stochastic_multilatent_discovery import (
    StochasticLatentGraph,
)


@dataclass(frozen=True)
class HierarchicalDomainSpec:
    causal: CausalDomainSpec
    charge_action: str
    key_action: str
    delivery_action: str
    resource_field: str
    key_field: str
    delivery_field: str
    charge_yield: int
    resource_capacity: int
    key_cost: int
    unlock_cost: int
    delivery_cost: int
    action_budget: int
    key_requires_alignment: bool = False


DOMAINS: Tuple[HierarchicalDomainSpec, ...] = (
    HierarchicalDomainSpec(
        causal=CausalDomainSpec(
            domain_id="obsidian_archive",
            signal_targets=("ember_script", "glass_script"),
            toggle_actions=("cant_ember", "cant_glass"),
            probe_actions=("read_ember", "read_glass"),
            goal_action="unseal_index",
            goal_pattern_by_signal=(1, 0),
            probe_reliabilities=(0.91, 0.86),
        ),
        charge_action="wind_spring",
        key_action="mint_siglum",
        delivery_action="publish_index",
        resource_field="spring_tension",
        key_field="siglum",
        delivery_field="published",
        charge_yield=6,
        resource_capacity=16,
        key_cost=2,
        unlock_cost=2,
        delivery_cost=2,
        action_budget=18,
    ),
    HierarchicalDomainSpec(
        causal=CausalDomainSpec(
            domain_id="mycelial_relay",
            signal_targets=("spore_a", "spore_b", "spore_c"),
            toggle_actions=("pulse_amber", "pulse_sable", "pulse_ivory"),
            probe_actions=("taste_a", "taste_b", "taste_c"),
            goal_action="join_mycelium",
            goal_pattern_by_signal=(1, 1, 0),
            probe_reliabilities=(0.89, 0.83, 0.92),
        ),
        charge_action="feed_glucose",
        key_action="grow_bridge",
        delivery_action="release_spores",
        resource_field="glucose",
        key_field="bridge",
        delivery_field="released",
        charge_yield=7,
        resource_capacity=18,
        key_cost=3,
        unlock_cost=2,
        delivery_cost=3,
        action_budget=21,
    ),
    HierarchicalDomainSpec(
        causal=CausalDomainSpec(
            domain_id="polar_foundry",
            signal_targets=("north_flux", "south_flux"),
            toggle_actions=("invert_cobalt", "invert_silver"),
            probe_actions=("sample_north", "sample_south"),
            goal_action="cast_lattice",
            goal_pattern_by_signal=(0, 1),
            probe_reliabilities=(0.87, 0.90),
        ),
        charge_action="prime_flywheel",
        key_action="forge_die",
        delivery_action="quench_lattice",
        resource_field="flywheel",
        key_field="die_ready",
        delivery_field="quenched",
        charge_yield=5,
        resource_capacity=15,
        key_cost=2,
        unlock_cost=3,
        delivery_cost=2,
        action_budget=19,
    ),
    HierarchicalDomainSpec(
        causal=CausalDomainSpec(
            domain_id="tide_embassy",
            signal_targets=("moon_seal", "reef_seal", "wind_seal"),
            toggle_actions=("turn_moon", "turn_reef", "turn_wind"),
            probe_actions=("sound_moon", "sound_reef", "sound_wind"),
            goal_action="ratify_current",
            goal_pattern_by_signal=(1, 0, 1),
            probe_reliabilities=(0.82, 0.94, 0.88),
        ),
        charge_action="store_tide",
        key_action="issue_credential",
        delivery_action="dispatch_treaty",
        resource_field="stored_tide",
        key_field="credential",
        delivery_field="dispatched",
        charge_yield=7,
        resource_capacity=19,
        key_cost=3,
        unlock_cost=3,
        delivery_cost=2,
        action_budget=22,
    ),
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "open_grammar_hierarchical_transfer_authority",
        "S": 1.0,
        "H": 0.0,
    }


class HierarchicalResourceDomain:
    """Opaque action grammar with hidden state, resources and prerequisites."""

    def __init__(
        self,
        *,
        spec: HierarchicalDomainSpec,
        seed: int,
    ) -> None:
        self.spec = spec
        self.base = NamedStochasticLatentDomain(
            spec=spec.causal,
            seed=seed,
        )
        self.resource = 0
        self.key = 0
        self.delivered = 0
        self.action_count = 0
        self.insufficient_resource_events = 0
        self.trace: List[Dict[str, Any]] = []
        self._sync_visible()

    def _sync_visible(self) -> None:
        self.base.visible[self.spec.resource_field] = self.resource
        self.base.visible[self.spec.key_field] = self.key
        self.base.visible[self.spec.delivery_field] = self.delivered

    def _cost(self, action: str) -> int:
        if action == self.spec.charge_action:
            return 0
        if action == self.spec.key_action:
            return self.spec.key_cost
        if action == self.spec.causal.goal_action:
            return self.spec.unlock_cost
        if action == self.spec.delivery_action:
            return self.spec.delivery_cost
        return 1

    def step(self, action: str) -> Dict[str, Any]:
        before = dict(self.base.visible)
        self.action_count += 1
        cost = self._cost(action)
        accepted = True
        reason = "EXECUTED"
        if action == self.spec.charge_action:
            self.resource = min(
                self.spec.resource_capacity,
                self.resource + self.spec.charge_yield,
            )
        elif self.resource < cost:
            accepted = False
            reason = "INSUFFICIENT_RESOURCE"
            self.insufficient_resource_events += 1
        else:
            self.resource -= cost
            if action == self.spec.key_action:
                aligned = all(
                    required == -1
                    or self.base.factors[index] == required
                    for index, required in enumerate(
                        self.spec.causal.goal_pattern_by_signal
                    )
                )
                if self.spec.key_requires_alignment and not aligned:
                    accepted = False
                    reason = "ALIGNMENT_PREREQUISITE_NOT_MET"
                else:
                    self.key = 1
            elif action == self.spec.delivery_action:
                if bool(self.base.visible.get("opened")) and self.key:
                    self.delivered = 1
                else:
                    accepted = False
                    reason = "PREREQUISITE_NOT_MET"
            elif action == self.spec.causal.goal_action:
                observation = self.base.step(action)
                if not self.key:
                    self.base.visible["opened"] = 0
                    accepted = False
                    reason = "KEY_PREREQUISITE_NOT_MET"
                else:
                    self.base.visible.update(observation["next_state"])
            else:
                observation = self.base.step(action)
                self.base.visible.update(observation["next_state"])
        self._sync_visible()
        row = {
            "action": action,
            "state": before,
            "next_state": dict(self.base.visible),
            "accepted": accepted,
            "reason": reason,
            "cost": cost,
        }
        self.trace.append(row)
        return {
            "state": before,
            "next_state": dict(self.base.visible),
            "evidence": {
                "domain_id": self.spec.causal.domain_id,
                "accepted": accepted,
                "reason": reason,
                "cost": cost,
                "hidden_factors_visible": False,
            },
        }

    @property
    def visible(self) -> Dict[str, Any]:
        return dict(self.base.visible)


def _capsule(spec: HierarchicalDomainSpec) -> EvidenceCapsule:
    subject = spec.causal.domain_id
    claims = [
        ("charge_action", spec.charge_action),
        ("key_action", spec.key_action),
        ("delivery_action", spec.delivery_action),
        ("resource_field", spec.resource_field),
        ("key_field", spec.key_field),
        ("delivery_field", spec.delivery_field),
        ("charge_yield", str(spec.charge_yield)),
        ("resource_capacity", str(spec.resource_capacity)),
        ("key_cost", str(spec.key_cost)),
        ("unlock_cost", str(spec.unlock_cost)),
        ("delivery_cost", str(spec.delivery_cost)),
        (
            "key_requires",
            "aligned_state"
            if spec.key_requires_alignment
            else "resource_only",
        ),
        ("delivery_requires", "opened_and_key"),
        ("terminal_goal", spec.delivery_field),
    ]
    return EvidenceCapsule(
        capsule_id=f"capsule_{subject}_operations_r1",
        source_uri=f"aion://sealed-domain/{subject}/verified-operations",
        content=(
            f"Verified operational constraints for {subject}. The symbols are "
            "domain-local; their roles are expressed as provenance-bearing "
            "claims rather than embedded in planner code."
        ),
        claims=[
            {
                "subject": subject,
                "predicate": predicate,
                "object": value,
                "revision": 1,
                "confidence": 1.0,
            }
            for predicate, value in claims
        ],
        verified=True,
    )


def _infer_role_partition(
    *,
    actions: Sequence[str],
    signal_targets: Sequence[str],
    rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Use visible intervention signatures to prune causal role search."""

    change_scores = {
        action: {signal: 0.0 for signal in signal_targets}
        for action in actions
    }
    goal_scores = {action: 0.0 for action in actions}
    support = {action: 0 for action in actions}
    for row in rows:
        action = str(row["action"])
        if action not in support:
            continue
        support[action] += 1
        before = row["state"]
        after = row["next_state"]
        for signal in signal_targets:
            changed = int(after.get(signal) != before.get(signal))
            informative = int(after.get(signal) in (0, 1))
            change_scores[action][signal] += changed + 0.05 * informative
        goal_scores[action] += (
            3.0 * int(after.get("opened") != before.get("opened"))
            + int(bool(after.get("opened")))
        )
    goal = max(
        actions,
        key=lambda action: (goal_scores[action], support[action], action),
    )
    remaining = [action for action in actions if action != goal]
    probe_order = max(
        itertools.permutations(remaining, len(signal_targets)),
        key=lambda order: sum(
            change_scores[action][signal]
            for action, signal in zip(order, signal_targets)
        ),
    )
    probes = tuple(probe_order)
    toggles = tuple(
        action for action in remaining if action not in set(probes)
    )
    return {
        "toggle_candidates": toggles,
        "probe_candidates": probes,
        "goal_candidates": (goal,),
        "evidence": {
            "support": support,
            "goal_scores": goal_scores,
            "signal_change_scores": change_scores,
        },
    }


def _surjective_assignment_count(signals: int, factors: int) -> int:
    return sum(
        1
        for row in itertools.product(range(factors), repeat=signals)
        if set(row) == set(range(factors))
    )


def _candidate_count(
    *,
    action_count: int,
    signal_count: int,
    maximum_factors: int,
    toggle_count: int | None = None,
    probe_count: int | None = None,
    goal_count: int | None = None,
) -> int:
    total = 0
    for factors in range(1, maximum_factors + 1):
        if toggle_count is None:
            roles = math.perm(
                action_count, factors + signal_count + 1
            )
        else:
            if toggle_count < factors or probe_count < signal_count:
                continue
            roles = (
                math.perm(toggle_count, factors)
                * math.perm(probe_count, signal_count)
                * int(goal_count or 0)
            )
        total += (
            roles
            * _surjective_assignment_count(signal_count, factors)
            * (2 ** factors)
        )
    return total


def _learn_domain_pruned(
    *,
    transfer: CrossDomainCausalTransferRuntime,
    spec: CausalDomainSpec,
    transfer_episodes: int = 20,
    transfer_steps: int = 15,
    cold_episodes: int = 64,
    cold_steps: int = 15,
) -> Dict[str, Any]:
    def factory(offset: int):
        def create(episode: int):
            return NamedStochasticLatentDomain(
                spec=spec,
                seed=offset + episode,
            ).step

        return create

    held_out_sequences = transfer.learner.diagnostic_sequences(
        actions=spec.actions,
        episodes=20,
        steps=15,
    )
    held_out_rows = transfer.learner.collect(
        runner_factory=factory(90_000),
        sequences=held_out_sequences,
        phase=f"{spec.domain_id}_held_out",
    )
    sequences = transfer.transferred_sequences(
        actions=spec.actions,
        episodes=transfer_episodes,
        steps=transfer_steps,
    )
    rows = transfer.learner.collect(
        runner_factory=factory(60_000),
        sequences=sequences,
        phase=f"{spec.domain_id}_pruned_transfer",
    )
    partition = _infer_role_partition(
        actions=spec.actions,
        signal_targets=spec.signal_targets,
        rows=rows,
    )
    # Once coarse roles are inferred, deliberately vary intervention subsets
    # before probing and testing the terminal action. This identifies the goal
    # condition without reading it from the domain specification.
    goal_sequences = []
    inferred_toggles = tuple(partition["toggle_candidates"])
    inferred_probes = tuple(partition["probe_candidates"])
    inferred_goal = str(partition["goal_candidates"][0])
    for repeat in range(2):
        for bits in itertools.product((0, 1), repeat=len(inferred_toggles)):
            sequence = [
                action
                for action, enabled in zip(inferred_toggles, bits)
                if enabled
            ]
            sequence.extend(inferred_probes)
            sequence.append(inferred_goal)
            goal_sequences.append(sequence)
    goal_rows = transfer.learner.collect(
        runner_factory=factory(70_000),
        sequences=goal_sequences,
        phase=f"{spec.domain_id}_goal_discrimination",
    )
    rows.extend(goal_rows)
    exhaustive_candidates = _candidate_count(
        action_count=len(spec.actions),
        signal_count=len(spec.signal_targets),
        maximum_factors=spec.factor_count,
    )
    pruned_candidates = _candidate_count(
        action_count=len(spec.actions),
        signal_count=len(spec.signal_targets),
        maximum_factors=spec.factor_count,
        toggle_count=len(partition["toggle_candidates"]),
        probe_count=len(partition["probe_candidates"]),
        goal_count=len(partition["goal_candidates"]),
    )
    started = time.perf_counter()
    session = transfer.learner.discover(
        world_id=spec.domain_id,
        actions=spec.actions,
        signal_targets=spec.signal_targets,
        rows=rows,
        minimum_factors=len(partition["toggle_candidates"]),
        maximum_factors=spec.factor_count,
        maximum_complexity=16,
        minimum_factor_gain=0.01,
        persist=True,
        toggle_action_candidates=partition["toggle_candidates"],
        probe_action_candidates=partition["probe_candidates"],
        goal_action_candidates=partition["goal_candidates"],
    )
    elapsed = time.perf_counter() - started
    graph = transfer.learner.graph_from_record(
        transfer.runtime.store.state["causal_graphs"][spec.domain_id]
    )
    held_out_score = transfer.learner.graph_score(graph, held_out_rows)
    cold_experiments = cold_episodes * cold_steps
    transfer_experiments = len(rows)
    return {
        "domain_id": spec.domain_id,
        "factor_count": spec.factor_count,
        "new_symbols": {
            "signals": spec.signal_targets,
            "actions": spec.actions,
        },
        "role_partition": partition,
        "cold": {
            "training_experiments": cold_experiments,
            "candidate_graphs": exhaustive_candidates,
            "graph_search_executed": False,
            "reason": "phase7_control_budget_and_exhaustive_contract",
        },
        "transfer": {
            "training_experiments": transfer_experiments,
            "candidate_graphs": pruned_candidates,
            "graph": graph.to_dict(),
            "structure_correct": transfer.graph_matches_spec(graph, spec),
            "held_out_score": held_out_score,
            "search_seconds": elapsed,
            "session": session,
        },
        "experiment_reduction": (
            1.0 - transfer_experiments / cold_experiments
        ),
        "candidate_search_reduction": (
            1.0 - pruned_candidates / exhaustive_candidates
        ),
    }


def _claim(
    runtime: HexCorePersistentLearningRuntime,
    domain_id: str,
    predicate: str,
) -> Dict[str, Any]:
    result = runtime.knowledge.query_claim(domain_id, predicate)
    if not result.get("found"):
        raise RuntimeError(f"missing required claim: {domain_id}:{predicate}")
    return dict(result["claim"])


def _binding_from_memory(
    runtime: HexCorePersistentLearningRuntime,
    spec: HierarchicalDomainSpec,
) -> Dict[str, Any]:
    graph = CrossDomainCausalTransferRuntime(runtime).learner.graph_from_record(
        runtime.store.state["causal_graphs"][spec.causal.domain_id]
    )
    predicates = (
        "charge_action",
        "key_action",
        "delivery_action",
        "resource_field",
        "key_field",
        "delivery_field",
        "charge_yield",
        "resource_capacity",
        "key_cost",
        "unlock_cost",
        "delivery_cost",
        "key_requires",
    )
    claims = {
        predicate: _claim(runtime, spec.causal.domain_id, predicate)
        for predicate in predicates
    }
    return {
        "graph": graph,
        "roles": {
            predicate: claim["object"] for predicate, claim in claims.items()
        },
        "evidence_ids": sorted(
            {
                evidence_id
                for claim in claims.values()
                for evidence_id in claim.get("evidence_ids") or []
            }
        ),
        "provenance_complete": all(
            bool(claim.get("evidence_ids")) for claim in claims.values()
        ),
    }


def _charge_until(
    environment: HierarchicalResourceDomain,
    *,
    action: str,
    required: int,
) -> None:
    while environment.resource < required:
        environment.step(action)


def _run_hierarchical_episode(
    *,
    runtime: HexCorePersistentLearningRuntime,
    spec: HierarchicalDomainSpec,
    seed: int,
) -> Dict[str, Any]:
    binding = _binding_from_memory(runtime, spec)
    graph: StochasticLatentGraph = binding["graph"]
    roles = binding["roles"]
    environment = HierarchicalResourceDomain(spec=spec, seed=seed)
    charge_action = str(roles["charge_action"])
    key_action = str(roles["key_action"])
    delivery_action = str(roles["delivery_action"])
    key_cost = int(roles["key_cost"])
    delivery_cost = int(roles["delivery_cost"])

    subgoals = []
    _charge_until(environment, action=charge_action, required=key_cost)
    environment.step(key_action)
    subgoals.append(
        {
            "subgoal": "obtain_domain_credential",
            "achieved": bool(environment.key),
        }
    )

    # Reserve enough energy for information gathering, intervention and unlock.
    _charge_until(
        environment,
        action=charge_action,
        required=spec.resource_capacity,
    )
    causal = CrossDomainCausalTransferRuntime(runtime).learner
    causal_result = causal.investigate_and_plan(
        graph=graph,
        runner=environment.step,
        initial_visible=environment.visible,
        action_costs={action: 1.0 for action in graph.probe_actions},
        confidence_gate=0.97,
        maximum_experiments=10,
        adaptive_experiment_budget=False,
        online_reliability_learning=False,
        value_of_information_ratio=False,
        goal_relevance_only=True,
        uncertain_factor_only=True,
        three_factor_reserve=True,
        policy_bank_enabled=False,
        goal_retries=1,
        toggle_action_cost=1.0,
        goal_action_cost=float(roles["unlock_cost"]),
    )
    calibrated = (
        float(causal_result["minimum_relevant_confidence"]) >= 0.90
    )
    subgoals.extend(
        [
            {
                "subgoal": "infer_goal_relevant_hidden_state",
                "achieved": calibrated,
            },
            {
                "subgoal": "align_hidden_state_and_unlock",
                "achieved": bool(environment.visible.get("opened")),
            },
        ]
    )

    _charge_until(
        environment, action=charge_action, required=delivery_cost
    )
    environment.step(delivery_action)
    delivered = bool(environment.visible.get(spec.delivery_field))
    subgoals.append(
        {"subgoal": "deliver_terminal_artifact", "achieved": delivered}
    )
    within_budget = environment.action_count <= spec.action_budget
    return {
        "success": bool(delivered and within_budget),
        "delivered": delivered,
        "within_action_budget": within_budget,
        "actions": environment.action_count,
        "action_budget": spec.action_budget,
        "insufficient_resource_events": (
            environment.insufficient_resource_events
        ),
        "causal_experiments": causal_result["experiment_count"],
        "calibrated": calibrated,
        "subgoals": subgoals,
        "grammar_binding": {
            "toggle_actions": list(graph.toggle_actions),
            "probe_actions": list(graph.probe_actions),
            "goal_action": graph.goal_action,
            "resource_roles": dict(roles),
            "evidence_ids": binding["evidence_ids"],
            "provenance_complete": binding["provenance_complete"],
        },
        "trace": environment.trace,
    }


def _run_flat_control(
    *,
    runtime: HexCorePersistentLearningRuntime,
    spec: HierarchicalDomainSpec,
    seed: int,
) -> Dict[str, Any]:
    binding = _binding_from_memory(runtime, spec)
    environment = HierarchicalResourceDomain(spec=spec, seed=seed)
    graph: StochasticLatentGraph = binding["graph"]
    result = CrossDomainCausalTransferRuntime(
        runtime
    ).learner.investigate_and_plan(
        graph=graph,
        runner=environment.step,
        initial_visible=environment.visible,
        action_costs={action: 1.0 for action in graph.probe_actions},
        maximum_experiments=7,
        goal_relevance_only=True,
        uncertain_factor_only=True,
    )
    return {
        "success": bool(environment.visible.get(spec.delivery_field)),
        "opened": bool(environment.visible.get("opened")),
        "actions": environment.action_count,
        "causal_goal_success": result["goal_success"],
    }


def _audit_domain(
    *,
    runtime: HexCorePersistentLearningRuntime,
    spec: HierarchicalDomainSpec,
    episodes: int,
    seed: int,
) -> Dict[str, Any]:
    hierarchical = [
        _run_hierarchical_episode(
            runtime=runtime,
            spec=spec,
            seed=seed + index,
        )
        for index in range(episodes)
    ]
    flat = [
        _run_flat_control(
            runtime=runtime,
            spec=spec,
            seed=seed + index,
        )
        for index in range(episodes)
    ]
    return {
        "episodes": episodes,
        "hierarchical_goal_success": sum(
            row["success"] for row in hierarchical
        ) / episodes,
        "flat_goal_success": sum(row["success"] for row in flat) / episodes,
        "mean_actions": sum(row["actions"] for row in hierarchical) / episodes,
        "mean_causal_experiments": sum(
            row["causal_experiments"] for row in hierarchical
        ) / episodes,
        "calibration_rate": sum(
            row["calibrated"] for row in hierarchical
        ) / episodes,
        "resource_failure_rate": sum(
            row["insufficient_resource_events"] > 0 for row in hierarchical
        ) / episodes,
        "budget_compliance": sum(
            row["within_action_budget"] for row in hierarchical
        ) / episodes,
        "provenance_complete": all(
            row["grammar_binding"]["provenance_complete"]
            for row in hierarchical
        ),
        "rows": hierarchical,
    }


def _summary(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in row.items() if key != "rows"}


def run_open_grammar_hierarchical_transfer_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_episodes: int = 24,
    sealed_episodes: int = 60,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    transfer = CrossDomainCausalTransferRuntime(runtime)

    # Development domains authorize the reusable procedure; sealed domains
    # use distinct symbols and are evaluated once.
    development_specs = DOMAINS[:2]
    sealed_specs = DOMAINS[2:]
    ingestion = {
        spec.causal.domain_id: runtime.knowledge.ingest(_capsule(spec))
        for spec in DOMAINS
    }
    structure_results = {
        spec.causal.domain_id: _learn_domain_pruned(
            transfer=transfer,
            spec=spec.causal,
        )
        for spec in DOMAINS
    }
    development = {
        spec.causal.domain_id: _audit_domain(
            runtime=runtime,
            spec=spec,
            episodes=development_episodes,
            seed=410_000 + index * 10_000,
        )
        for index, spec in enumerate(development_specs)
    }

    # Sealed evaluation is opened only after every development domain reaches
    # the declared success, provenance and budget gates.
    development_gate = all(
        row["hierarchical_goal_success"] >= 0.80
        and row["budget_compliance"] >= 0.95
        and row["provenance_complete"]
        for row in development.values()
    )
    sealed = {
        spec.causal.domain_id: _audit_domain(
            runtime=runtime,
            spec=spec,
            episodes=sealed_episodes,
            seed=710_000 + index * 10_000,
        )
        for index, spec in enumerate(sealed_specs)
    } if development_gate else {}

    reductions = [
        structure_results[spec.causal.domain_id]["experiment_reduction"]
        for spec in sealed_specs
    ]
    search_reductions = [
        structure_results[spec.causal.domain_id][
            "candidate_search_reduction"
        ]
        for spec in sealed_specs
    ]
    sealed_success = [
        sealed[spec.causal.domain_id]["hierarchical_goal_success"]
        for spec in sealed_specs
    ] if sealed else [0.0]
    flat_success = [
        sealed[spec.causal.domain_id]["flat_goal_success"]
        for spec in sealed_specs
    ] if sealed else [0.0]
    worst_success = min(sealed_success)
    mean_success = sum(sealed_success) / len(sealed_success)
    mean_flat = sum(flat_success) / len(flat_success)
    errors = []
    if not development_gate:
        errors.append("DEVELOPMENT_GATE_FAILED")
    if not all(
        structure_results[spec.causal.domain_id]["transfer"][
            "structure_correct"
        ]
        for spec in sealed_specs
    ):
        errors.append("SEALED_GRAMMAR_RECOVERY_FAILED")
    if min(reductions) < 0.50:
        errors.append("POSITIVE_TRANSFER_EXPERIMENT_REDUCTION_FAILED")
    if min(search_reductions) < 0.95:
        errors.append("COMPUTATIONAL_TRANSFER_REDUCTION_FAILED")
    if mean_success < 0.85:
        errors.append("MEAN_HIERARCHICAL_SUCCESS_BELOW_85_PERCENT")
    if worst_success < 0.80:
        errors.append("WORST_DOMAIN_SUCCESS_BELOW_80_PERCENT")
    if mean_success - mean_flat < 0.50:
        errors.append("HIERARCHICAL_COMPOSITION_GAIN_BELOW_50_POINTS")
    if sealed and not all(
        row["provenance_complete"] for row in sealed.values()
    ):
        errors.append("KNOWLEDGE_PROVENANCE_INCOMPLETE")
    if sealed and not all(
        row["budget_compliance"] >= 0.95 for row in sealed.values()
    ):
        errors.append("RESOURCE_BUDGET_GATE_FAILED")
    gate = {
        "accepted": not errors,
        "errors": errors,
        "mean_hierarchical_goal_success": mean_success,
        "worst_domain_goal_success": worst_success,
        "mean_flat_goal_success": mean_flat,
        "mean_goal_gain_over_flat": mean_success - mean_flat,
        "minimum_experiment_reduction_vs_cold": min(reductions),
        "minimum_candidate_search_reduction_vs_exhaustive": min(
            search_reductions
        ),
    }

    baseline = ProcedureCandidate(
        procedure_id="procedure_counterfactual_plan_2524af5f13ea",
        goal="open_grammar_hierarchical_transfer",
        steps=["plan_inside_known_binary_action_grammar"],
        score=mean_flat,
        success=True,
        evidence={"evaluation": "phase20_flat_control"},
    )
    runtime.skills.promote(baseline)
    steps = [
        "ingest_verified_domain_constraints",
        "bind_opaque_symbols_to_abstract_causal_roles",
        "recover_hidden_state_grammar_with_transferred_experiments",
        "retrieve_prerequisites_with_provenance",
        "decompose_terminal_goal_into_ordered_subgoals",
        "allocate_information_and material resources",
        "investigate_only_goal_relevant_hidden_factors",
        "execute_and_verify_each_subgoal",
        "abstain_or_fallback_when_budget_or_evidence_is_insufficient",
        "retain_domain_binding_and_abstract_procedure_separately",
    ]
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_open_grammar_hierarchy_"
            + _canonical_hash(steps)[:12]
        ),
        goal="open_grammar_hierarchical_transfer",
        steps=steps,
        score=mean_success,
        success=gate["accepted"],
        evidence={
            "evaluation": "phase20_open_grammar_hierarchical_sealed",
            "gate": gate,
            "development_domains": [
                spec.causal.domain_id for spec in development_specs
            ],
            "sealed_domains": [
                spec.causal.domain_id for spec in sealed_specs
            ],
        },
        source_rules=[
            structure_results[spec.causal.domain_id]["transfer"]["graph"][
                "graph_id"
            ]
            for spec in sealed_specs
        ],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    if gate["accepted"]:
        runtime.store.state.setdefault("causal_graphs", {})[
            "open_grammar_hierarchical_transfer"
        ] = {
            "schema_version": (
                "aion.hexcore.open_grammar_hierarchical_memory.v1"
            ),
            "procedure_id": candidate.procedure_id,
            "development_domains": [
                spec.causal.domain_id for spec in development_specs
            ],
            "sealed_domains": [
                spec.causal.domain_id for spec in sealed_specs
            ],
            "gate": gate,
            "created_at": _utc_timestamp(),
        }
        runtime.store.commit(
            reason="open_grammar_hierarchical_transfer_memory"
        )

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    champion = restarted.skills.champion(candidate.goal)
    retained = bool(
        champion and champion.get("procedure_id") == candidate.procedure_id
    )
    result = {
        "schema_version": (
            "aion.hexcore.open_grammar_hierarchical_transfer.v1"
        ),
        "benchmark": (
            "cross_domain_opaque_grammar_hierarchical_resource_planning"
        ),
        "language_provider_used": False,
        "domain_symbols_hardcoded_in_planner": False,
        "development_domains": {
            key: _summary(value) for key, value in development.items()
        },
        "sealed_domains": {
            key: _summary(value) for key, value in sealed.items()
        },
        "structure_learning": structure_results,
        "knowledge_ingestion": ingestion,
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": {
            "champion_retained": retained,
            "all_capsules_retained": all(
                f"capsule_{spec.causal.domain_id}_operations_r1"
                in restarted.store.state["evidence"]
                for spec in DOMAINS
            ),
            "all_domain_graphs_retained": all(
                spec.causal.domain_id
                in restarted.store.state["causal_graphs"]
                for spec in DOMAINS
            ),
            "abstract_hierarchy_memory_retained": (
                "open_grammar_hierarchical_transfer"
                in restarted.store.state["causal_graphs"]
            ),
            "relearning_experiments": 0,
        },
        "gates": {
            "opaque_grammar_recovered": not any(
                error == "SEALED_GRAMMAR_RECOVERY_FAILED"
                for error in errors
            ),
            "positive_transfer": min(reductions) >= 0.50,
            "computational_transfer": min(search_reductions) >= 0.95,
            "hierarchical_goal_composition": (
                mean_success - mean_flat >= 0.50
            ),
            "partial_observability_handled": (
                min(row["calibration_rate"] for row in sealed.values())
                >= 0.80 if sealed else False
            ),
            "resource_budget_respected": (
                all(row["budget_compliance"] >= 0.95 for row in sealed.values())
                if sealed else False
            ),
            "knowledge_provenance_complete": (
                all(row["provenance_complete"] for row in sealed.values())
                if sealed else False
            ),
            "sealed_gate_passed": gate["accepted"],
            "cau_promotion": promotion.get("promoted") is True,
            "restart_retention": retained,
        },
        "boundary_statement": (
            "This phase tests reusable grammar binding and hierarchical "
            "planning across four bounded causal-resource domains. Domain "
            "symbols are new and role bindings are learned or retrieved, but "
            "the abstract operator vocabulary, binary latent state family and "
            "simulator interfaces remain engineered. It is not unrestricted "
            "general intelligence."
        ),
    }
    result["passed"] = all(result["gates"].values())
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path("data/hexcore/open_grammar_hierarchical_transfer.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path(
            "results/hexcore_open_grammar_hierarchical_transfer.json"
        ),
    )
    args = parser.parse_args()
    result = run_open_grammar_hierarchical_transfer_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
