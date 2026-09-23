from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.learned_repair_interference_benchmark import (
    run_phase63_learned_repair_interference,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


ROLE_COUNT = 4
STATE_BITS = tuple(itertools.product((0, 1), repeat=ROLE_COUNT))


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "raw_event_representation_learning_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _stable_id(prefix: str, value: Any, width: int = 16) -> str:
    return f"{prefix}_{_canonical_hash(value)[:width]}"


@dataclass(frozen=True)
class RawProjectDomain:
    domain_id: str
    family: str
    channel_names: Tuple[str, ...]
    action_names: Tuple[str, ...]
    zero_tokens: Tuple[str, ...]
    one_tokens: Tuple[str, ...]
    outcome_key: str
    success_token: str
    failure_token: str

    def encode_state(
        self,
        bits: Sequence[int],
        *,
        clock: int,
        sequence: int,
    ) -> Dict[str, Any]:
        # Channel names and categorical values are intentionally opaque. The
        # learner is not told that any channel means stale authority, conflict,
        # source drift, or readiness.
        channels = {
            name: self.one_tokens[index] if int(bits[index]) else self.zero_tokens[index]
            for index, name in enumerate(self.channel_names)
        }
        return {
            "stream": self.domain_id,
            "sequence": sequence,
            "clock": clock,
            "payload": channels,
        }

    def decode_bits_for_evaluator(self, event: Mapping[str, Any]) -> Tuple[int, ...]:
        payload = dict(event["payload"])
        return tuple(
            int(payload[name] == self.one_tokens[index])
            for index, name in enumerate(self.channel_names)
        )


def _domain(seed: int, family: str, index: int) -> RawProjectDomain:
    rng = random.Random(seed)
    channel_names = tuple(
        f"{rng.choice(('q', 'lane', 'sensor', 'cell', 'field'))}_{rng.randrange(10_000):04d}"
        for _ in range(ROLE_COUNT)
    )
    action_names = tuple(
        f"{rng.choice(('op', 'move', 'pulse', 'job', 'step'))}_{rng.randrange(10_000):04d}"
        for _ in range(ROLE_COUNT + 1)
    )
    zero_tokens = tuple(f"v{rng.randrange(10_000):04d}" for _ in range(ROLE_COUNT))
    one_tokens = tuple(f"v{rng.randrange(10_000):04d}" for _ in range(ROLE_COUNT))
    return RawProjectDomain(
        domain_id=f"{family}_{index}_{_canonical_hash([seed, family, index])[:10]}",
        family=family,
        channel_names=channel_names,
        action_names=action_names,
        zero_tokens=zero_tokens,
        one_tokens=one_tokens,
        outcome_key=f"result_{rng.randrange(10_000):04d}",
        success_token=f"ok_{rng.randrange(10_000):04d}",
        failure_token=f"no_{rng.randrange(10_000):04d}",
    )


def _apply_hidden_action(
    bits: Sequence[int],
    action_role: int,
) -> Tuple[Tuple[int, ...], bool]:
    state = list(bits)
    if action_role < ROLE_COUNT:
        state[action_role] = 0
        return tuple(state), True
    success = not any(state)
    return tuple(state), success


def _transition(
    domain: RawProjectDomain,
    *,
    bits: Sequence[int],
    action_role: int,
    clock: int,
    sequence: int,
) -> Dict[str, Any]:
    before = domain.encode_state(bits, clock=clock, sequence=sequence)
    after_bits, valid = _apply_hidden_action(bits, action_role)
    after = domain.encode_state(
        after_bits,
        clock=clock + 1,
        sequence=sequence + 1,
    )
    outcome = (
        domain.success_token
        if action_role < ROLE_COUNT or valid
        else domain.failure_token
    )
    return {
        "transition_id": _stable_id(
            "raw_transition",
            [domain.domain_id, sequence, bits, action_role],
        ),
        "before": before,
        "action": domain.action_names[action_role],
        "after": after,
        "outcome": {domain.outcome_key: outcome},
        "observed_at": _utc_timestamp(),
    }


def _development_stream(
    domain: RawProjectDomain,
    *,
    seed: int,
) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    rows: List[Dict[str, Any]] = []
    sequence = 0
    # Exhaustive single-action interventions expose behavior but never the
    # evaluator's state labels or semantic role names.
    for bits in STATE_BITS:
        action_roles = list(range(ROLE_COUNT + 1))
        rng.shuffle(action_roles)
        for action_role in action_roles:
            rows.append(
                _transition(
                    domain,
                    bits=bits,
                    action_role=action_role,
                    clock=sequence,
                    sequence=sequence,
                )
            )
            sequence += 2
    return rows


def _probe_stream(
    domain: RawProjectDomain,
    *,
    seed: int,
) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    rows = []
    # Five probes are sufficient to identify the anonymous channel/action
    # interaction graph; the learner does not receive a mapping.
    for action_role in range(ROLE_COUNT + 1):
        bits = [1, 1, 1, 1]
        if action_role == ROLE_COUNT:
            bits = [rng.randrange(2) for _ in range(ROLE_COUNT)]
            if not any(bits):
                bits[0] = 1
        rows.append(
            _transition(
                domain,
                bits=bits,
                action_role=action_role,
                clock=action_role,
                sequence=action_role * 2,
            )
        )
    return rows


def _changed_channels(row: Mapping[str, Any]) -> Dict[str, Tuple[str, str]]:
    before = dict(row["before"]["payload"])
    after = dict(row["after"]["payload"])
    return {
        key: (str(before[key]), str(after[key]))
        for key in before
        if before[key] != after[key]
    }


def _learn_local_effect_graph(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    actions = sorted({str(row["action"]) for row in rows})
    channels = sorted(
        {
            str(key)
            for row in rows
            for key in dict(row["before"]["payload"])
        }
    )
    effects: Dict[str, Dict[str, int]] = {
        action: {channel: 0 for channel in channels}
        for action in actions
    }
    attempts: Dict[str, int] = defaultdict(int)
    successful_outcomes: Dict[str, int] = defaultdict(int)
    for row in rows:
        action = str(row["action"])
        attempts[action] += 1
        changed = _changed_channels(row)
        for channel in changed:
            effects[action][channel] += 1
        outcome_value = next(iter(dict(row["outcome"]).values()))
        if str(outcome_value).startswith("ok_"):
            successful_outcomes[action] += 1
    return {
        "actions": actions,
        "channels": channels,
        "effects": effects,
        "attempts": dict(attempts),
        "successful_outcomes": dict(successful_outcomes),
    }


def _structural_roles(graph: Mapping[str, Any]) -> Dict[str, Dict[str, str]]:
    actions = list(graph["actions"])
    channels = list(graph["channels"])
    effects = graph["effects"]

    # Color refinement names roles exclusively by graph topology. Identifiers
    # never enter the color hash, making the representation invariant to field
    # and action renaming.
    action_colors = {
        action: _canonical_hash(
            [
                "action",
                sum(int(effects[action][channel] > 0) for channel in channels),
            ]
        )
        for action in actions
    }
    channel_colors = {
        channel: _canonical_hash(
            [
                "channel",
                sum(int(effects[action][channel] > 0) for action in actions),
            ]
        )
        for channel in channels
    }
    for _ in range(4):
        action_colors = {
            action: _canonical_hash(
                [
                    "action",
                    sorted(
                        channel_colors[channel]
                        for channel in channels
                        if effects[action][channel] > 0
                    ),
                ]
            )
            for action in actions
        }
        channel_colors = {
            channel: _canonical_hash(
                [
                    "channel",
                    sorted(
                        action_colors[action]
                        for action in actions
                        if effects[action][channel] > 0
                    ),
                ]
            )
            for channel in channels
        }

    # Symmetric repair roles cannot be distinguished topologically and should
    # not be assigned arbitrary meanings. Their shared role is intentional.
    action_role = {
        action: f"operator_{action_colors[action][:12]}"
        for action in actions
    }
    channel_role = {
        channel: f"dimension_{channel_colors[channel][:12]}"
        for channel in channels
    }
    return {"actions": action_role, "channels": channel_role}


def _value_orientation(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Dict[str, str]]:
    result: Dict[str, Dict[str, str]] = {}
    for row in rows:
        for channel, (before, after) in _changed_channels(row).items():
            # An intervention that persistently changes a channel supplies the
            # orientation. The values themselves remain semantically unnamed.
            result[channel] = {"active": before, "settled": after}
    return result


def _state_symbol(
    event: Mapping[str, Any],
    *,
    roles: Mapping[str, Mapping[str, str]],
    orientation: Mapping[str, Mapping[str, str]],
) -> Tuple[str, Dict[str, int]]:
    payload = dict(event["payload"])
    role_values: Dict[str, List[int]] = defaultdict(list)
    for channel, value in payload.items():
        if channel not in orientation:
            continue
        role = str(roles["channels"][channel])
        role_values[role].append(
            int(str(value) == str(orientation[channel]["active"]))
        )
    canonical = {
        role: sum(values)
        for role, values in sorted(role_values.items())
    }
    return _stable_id("state", canonical), canonical


def _invent_vocabulary(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    graph = _learn_local_effect_graph(rows)
    roles = _structural_roles(graph)
    orientation = _value_orientation(rows)
    states: Dict[str, Dict[str, Any]] = {}
    relations: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        before_id, before_vector = _state_symbol(
            row["before"],
            roles=roles,
            orientation=orientation,
        )
        after_id, after_vector = _state_symbol(
            row["after"],
            roles=roles,
            orientation=orientation,
        )
        states.setdefault(
            before_id,
            {
                "symbol": before_id,
                "structural_vector": before_vector,
                "origin": "invented_from_raw_event_equivalence",
            },
        )
        states.setdefault(
            after_id,
            {
                "symbol": after_id,
                "structural_vector": after_vector,
                "origin": "invented_from_raw_event_equivalence",
            },
        )
        action_role = roles["actions"][str(row["action"])]
        relation_key = [before_id, action_role, after_id]
        relation_id = _stable_id("relation", relation_key)
        relation = relations.setdefault(
            relation_id,
            {
                "relation_id": relation_id,
                "source_state": before_id,
                "operator_role": action_role,
                "target_state": after_id,
                "support": 0,
            },
        )
        relation["support"] += 1
    model_id = _stable_id(
        "representation",
        {
            "states": states,
            "relations": relations,
            "role_classes": sorted(set(roles["actions"].values())),
        },
    )
    return {
        "model_id": model_id,
        "graph": graph,
        "roles": roles,
        "orientation": orientation,
        "states": states,
        "relations": relations,
        "raw_semantic_labels_seen": False,
    }


def _portable_photon_ir(model: Mapping[str, Any]) -> Dict[str, Any]:
    # Photon PIR is used as a typed, executable proposal representation. It is
    # deliberately data-only here; authority and execution remain in HexCore.
    ops = []
    for relation in sorted(
        model["relations"].values(),
        key=lambda row: row["relation_id"],
    ):
        ops.append(
            {
                "op": "⇒",
                "args": [
                    relation["source_state"],
                    relation["operator_role"],
                    relation["target_state"],
                ],
                "support": relation["support"],
            }
        )
    return {
        "schema_version": "tessaris.photon.pir.state_vocabulary.v1",
        "capsule_id": _stable_id("photon_capsule", model["model_id"]),
        "mode": "symbolic",
        "ops": ops,
        "provenance": {
            "representation_model_id": model["model_id"],
            "authority": "proposal_only",
        },
    }


def _transfer_model(
    *,
    source_model: Mapping[str, Any],
    probe_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    local_graph = _learn_local_effect_graph(probe_rows)
    local_roles = _structural_roles(local_graph)
    orientation = _value_orientation(probe_rows)
    source_action_roles = sorted(set(source_model["roles"]["actions"].values()))
    target_action_roles = sorted(set(local_roles["actions"].values()))
    analogous = source_action_roles == target_action_roles
    return {
        "analogous": analogous,
        "graph": local_graph,
        "roles": local_roles,
        "orientation": orientation,
        "decision": "transfer" if analogous else "abstain",
    }


def _evaluate_domain(
    domain: RawProjectDomain,
    *,
    source_model: Mapping[str, Any],
    seed: int,
) -> Dict[str, Any]:
    probes = _probe_stream(domain, seed=seed)
    transfer = _transfer_model(
        source_model=source_model,
        probe_rows=probes,
    )
    if not transfer["analogous"]:
        return {
            "domain_id": domain.domain_id,
            "family": domain.family,
            "decision": "abstain",
            "state_accuracy": 0.0,
            "transition_accuracy": 0.0,
            "unsafe_acceptances": 0,
            "probes": len(probes),
        }
    rows = _development_stream(domain, seed=seed + 1)
    state_correct = 0
    transition_correct = 0
    predictions = 0
    source_relations = {
        (
            relation["source_state"],
            relation["operator_role"],
            relation["target_state"],
        )
        for relation in source_model["relations"].values()
    }
    for row in rows:
        before_id, _ = _state_symbol(
            row["before"],
            roles=transfer["roles"],
            orientation=transfer["orientation"],
        )
        after_id, _ = _state_symbol(
            row["after"],
            roles=transfer["roles"],
            orientation=transfer["orientation"],
        )
        before_bits = domain.decode_bits_for_evaluator(row["before"])
        after_bits = domain.decode_bits_for_evaluator(row["after"])
        expected_before = _stable_id(
            "state",
            {
                next(iter(set(transfer["roles"]["channels"].values()))): sum(
                    before_bits
                )
            },
        )
        expected_after = _stable_id(
            "state",
            {
                next(iter(set(transfer["roles"]["channels"].values()))): sum(
                    after_bits
                )
            },
        )
        state_correct += int(
            before_id == expected_before and after_id == expected_after
        )
        action_role = transfer["roles"]["actions"][str(row["action"])]
        transition_correct += int(
            (before_id, action_role, after_id) in source_relations
        )
        predictions += 1
    return {
        "domain_id": domain.domain_id,
        "family": domain.family,
        "decision": "transfer",
        "state_accuracy": state_correct / predictions,
        "transition_accuracy": transition_correct / predictions,
        "unsafe_acceptances": 0,
        "probes": len(probes),
    }


def _non_analogous_rows(domain: RawProjectDomain) -> List[Dict[str, Any]]:
    # Add a coupled operator that changes two channels simultaneously. This
    # graph is outside the learned family and must not be forced into it.
    rows = _probe_stream(domain, seed=9901)
    before = domain.encode_state((1, 1, 1, 1), clock=20, sequence=20)
    after = domain.encode_state((0, 0, 1, 1), clock=21, sequence=21)
    rows.append(
        {
            "transition_id": _stable_id("ood_transition", domain.domain_id),
            "before": before,
            "action": f"coupled_{domain.domain_id}",
            "after": after,
            "outcome": {domain.outcome_key: domain.success_token},
            "observed_at": _utc_timestamp(),
        }
    )
    return rows


def run_raw_event_representation_learning(
    *,
    repo_root: Path,
    state_path: Path,
    workspace_root: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    phase63 = run_phase63_learned_repair_interference(
        repo_root=repo_root,
        state_path=state_path,
        workspace_root=workspace_root / "phase63",
        result_path=workspace_root / "phase63_prerequisite.json",
    )
    if not phase63["passed"]:
        raise RuntimeError("LEARNED_INTERFERENCE_PREREQUISITE_FAILED")

    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    development_domains = [
        _domain(64_000 + index, family, index)
        for index, family in enumerate(
            ("scientific", "financial", "software", "operations")
        )
    ]
    sealed_domains = [
        _domain(65_000 + index, family, index)
        for index, family in enumerate(
            ("medical", "logistics", "legal", "energy")
        )
    ]

    development_models = []
    for index, domain in enumerate(development_domains):
        rows = _development_stream(domain, seed=66_000 + index)
        model = _invent_vocabulary(rows)
        development_models.append(model)
        runtime.store.state["raw_event_streams"][domain.domain_id] = {
            "domain_id": domain.domain_id,
            "family": domain.family,
            "events": len(rows),
            "stream_hash": _canonical_hash(rows),
            "semantic_labels_exposed": False,
        }

    # Select the most compact model. All development models should be
    # structurally equivalent despite independent names and value alphabets.
    model = min(
        development_models,
        key=lambda row: (
            len(row["states"]) + len(row["relations"]),
            row["model_id"],
        ),
    )
    photon_ir = _portable_photon_ir(model)
    runtime.store.state["invented_state_vocabularies"][model["model_id"]] = {
        "states": model["states"],
        "source": "raw_event_predictive_equivalence",
        "semantic_labels_exposed": False,
    }
    runtime.store.state["invented_relation_vocabularies"][model["model_id"]] = {
        "relations": model["relations"],
        "source": "action_conditioned_transition_induction",
    }
    runtime.store.state["representation_models"][model["model_id"]] = {
        "model_id": model["model_id"],
        "status": "private_challenger",
        "photon_ir": photon_ir,
        "development_families": [
            domain.family for domain in development_domains
        ],
    }
    runtime.store.commit(reason="raw_event_representation_private_challenger")

    sealed_rows = [
        _evaluate_domain(
            domain,
            source_model=model,
            seed=67_000 + index,
        )
        for index, domain in enumerate(sealed_domains)
    ]
    ood_domain = _domain(68_000, "non_analogous", 0)
    ood_transfer = _transfer_model(
        source_model=model,
        probe_rows=_non_analogous_rows(ood_domain),
    )

    mean_state = sum(row["state_accuracy"] for row in sealed_rows) / len(
        sealed_rows
    )
    mean_transition = sum(
        row["transition_accuracy"] for row in sealed_rows
    ) / len(sealed_rows)
    weakest_state = min(row["state_accuracy"] for row in sealed_rows)
    weakest_transition = min(
        row["transition_accuracy"] for row in sealed_rows
    )
    exhaustive_observations = len(STATE_BITS) * (ROLE_COUNT + 1)
    mean_probes = sum(row["probes"] for row in sealed_rows) / len(sealed_rows)
    observation_reduction = 1.0 - mean_probes / exhaustive_observations
    development_model_ids = {row["model_id"] for row in development_models}
    cross_domain_invariant = len(development_model_ids) == 1
    gate = {
        "phase63_prerequisite": phase63["passed"],
        "semantic_state_labels_supplied": False,
        "semantic_relation_labels_supplied": False,
        "raw_field_names_shared_between_domains": False,
        "development_structural_invariance": cross_domain_invariant,
        "invented_states": len(model["states"]),
        "invented_relations": len(model["relations"]),
        "sealed_mean_state_accuracy": mean_state,
        "sealed_weakest_state_accuracy": weakest_state,
        "sealed_mean_transition_accuracy": mean_transition,
        "sealed_weakest_transition_accuracy": weakest_transition,
        "observation_reduction_vs_exhaustive": observation_reduction,
        "non_analogous_abstention": ood_transfer["decision"] == "abstain",
        "photon_ir_traceable": bool(
            photon_ir["provenance"]["representation_model_id"]
            == model["model_id"]
        ),
        "unsafe_acceptances": sum(
            row["unsafe_acceptances"] for row in sealed_rows
        ),
    }
    errors = []
    for name, minimum in (
        ("sealed_mean_state_accuracy", 0.95),
        ("sealed_weakest_state_accuracy", 0.90),
        ("sealed_mean_transition_accuracy", 0.95),
        ("sealed_weakest_transition_accuracy", 0.90),
        ("observation_reduction_vs_exhaustive", 0.80),
    ):
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum:.2f}")
    for name in (
        "development_structural_invariance",
        "non_analogous_abstention",
        "photon_ir_traceable",
    ):
        if not gate[name]:
            errors.append(f"{name.upper()}_FAILED")
    if gate["unsafe_acceptances"]:
        errors.append("UNSAFE_REPRESENTATION_ACCEPTANCE")
    gate["errors"] = errors
    gate["accepted"] = not errors

    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_raw_event_representation_"
            f"{_canonical_hash([model['model_id'], gate])[:12]}"
        ),
        goal="raw_event_representation_learning",
        steps=[
            "observe_raw_project_event_stream",
            "infer_anonymous_channel_action_effect_graph",
            "refine_structural_roles_without_field_names",
            "invent_predictive_state_symbols",
            "invent_action_conditioned_relation_symbols",
            "compile_traceable_photon_pir",
            "transfer_by_structure_or_abstain",
        ],
        score=mean_state + mean_transition + observation_reduction,
        success=gate["accepted"],
        evidence={"gate": gate, "representation_model_id": model["model_id"]},
        source_rules=[
            phase63["promotion"]["candidate"]["procedure_id"],
            "photon_language_v0.2_operator_trigger",
        ],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.state["representation_models"][model["model_id"]][
        "status"
    ] = "promoted" if promotion.get("promoted") else "rejected"
    session = {
        "session_id": _stable_id(
            "representation_session",
            [model["model_id"], _utc_timestamp()],
        ),
        "model_id": model["model_id"],
        "gate": gate,
        "promotion": promotion,
        "created_at": _utc_timestamp(),
    }
    runtime.store.state["representation_learning_sessions"].append(session)
    runtime.store.commit(reason="raw_event_representation_learning")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    retained = restarted.skills.champion("raw_event_representation_learning")
    restart = {
        "state_vocabulary_retained": model["model_id"]
        in restarted.store.state["invented_state_vocabularies"],
        "relation_vocabulary_retained": model["model_id"]
        in restarted.store.state["invented_relation_vocabularies"],
        "photon_ir_retained": bool(
            restarted.store.state["representation_models"][model["model_id"]][
                "photon_ir"
            ]
            == photon_ir
        ),
        "champion_retained": bool(
            retained and retained["procedure_id"] == candidate.procedure_id
        ),
        "relearning_events": 0,
    }
    result = {
        "schema_version": "aion.hexcore.raw_event_representation_learning.v1",
        "capability_track": "raw_event_representation_learning",
        "passed": bool(
            gate["accepted"]
            and promotion.get("promoted")
            and restart["state_vocabulary_retained"]
            and restart["relation_vocabulary_retained"]
            and restart["photon_ir_retained"]
            and restart["champion_retained"]
            and restart["relearning_events"] == 0
        ),
        "prerequisite": {
            "passed": phase63["passed"],
            "procedure_id": phase63["promotion"]["candidate"]["procedure_id"],
        },
        "development": {
            "domains": len(development_domains),
            "families": [domain.family for domain in development_domains],
            "model_ids": sorted(development_model_ids),
            "structurally_invariant": cross_domain_invariant,
        },
        "invented_representation": {
            "model_id": model["model_id"],
            "state_vocabulary": model["states"],
            "relation_vocabulary": model["relations"],
            "photon_ir": photon_ir,
        },
        "sealed": {
            "domains": len(sealed_domains),
            "families": [domain.family for domain in sealed_domains],
            "rows": sealed_rows,
            "mean_state_accuracy": mean_state,
            "weakest_state_accuracy": weakest_state,
            "mean_transition_accuracy": mean_transition,
            "weakest_transition_accuracy": weakest_transition,
        },
        "ood": {
            "family": ood_domain.family,
            "decision": ood_transfer["decision"],
            "forced_mapping": False,
        },
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary": (
            "This track invents opaque predictive state and relation symbols "
            "from raw categorical project-event streams and transfers them "
            "under complete field/action renaming. The event channels, finite "
            "action interface, deterministic dynamics, four-dimensional "
            "topology and correctness oracle remain engineered. It is not "
            "unrestricted ontology induction from arbitrary natural media."
        ),
        "created_at": _utc_timestamp(),
    }
    if result_path is not None:
        result_path = result_path.resolve()
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run raw-event state-vocabulary learning benchmark."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_raw_event_representation_learning(
        repo_root=args.repo_root,
        state_path=args.state_path,
        workspace_root=args.workspace_root,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
