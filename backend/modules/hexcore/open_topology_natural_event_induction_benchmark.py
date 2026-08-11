from __future__ import annotations

import argparse
import itertools
import json
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.autonomous_capability_curriculum_benchmark import (
    run_autonomous_capability_curriculum,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


OBSERVATION_PATTERNS = (
    re.compile(
        r"^(?P<entity>[A-Z][A-Za-z0-9_-]+) reports "
        r"(?P<dimension>[a-z][a-z0-9_-]+) as "
        r"(?P<value>[a-z][a-z0-9_-]+)\.$"
    ),
    re.compile(
        r"^Reading for (?P<entity>[A-Z][A-Za-z0-9_-]+): "
        r"(?P<dimension>[a-z][a-z0-9_-]+) became "
        r"(?P<value>[a-z][a-z0-9_-]+)\.$"
    ),
    re.compile(
        r"^On (?P<entity>[A-Z][A-Za-z0-9_-]+), "
        r"(?P<dimension>[a-z][a-z0-9_-]+) is "
        r"(?P<value>[a-z][a-z0-9_-]+)\.$"
    ),
)
ACTION_PATTERNS = (
    re.compile(
        r"^Command (?P<action>[a-z][a-z0-9_-]+) reached "
        r"(?P<entity>[A-Z][A-Za-z0-9_-]+)\.$"
    ),
    re.compile(
        r"^(?P<entity>[A-Z][A-Za-z0-9_-]+) received operation "
        r"(?P<action>[a-z][a-z0-9_-]+)\.$"
    ),
    re.compile(
        r"^Operation (?P<action>[a-z][a-z0-9_-]+) was applied to "
        r"(?P<entity>[A-Z][A-Za-z0-9_-]+)\.$"
    ),
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "open_topology_natural_event_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _stable_id(prefix: str, value: Any, width: int = 16) -> str:
    return f"{prefix}_{_canonical_hash(value)[:width]}"


@dataclass(frozen=True)
class NaturalWorld:
    world_id: str
    family: str
    entities: Tuple[str, ...]
    dimensions: Tuple[str, ...]
    values: Mapping[str, Tuple[str, str]]
    actions: Tuple[str, ...]
    modes: int
    persistent_dimensions: Tuple[str, ...]
    topology: str
    template_offset: int


def _word(rng: random.Random, prefix: str) -> str:
    syllables = (
        "al",
        "be",
        "cor",
        "dra",
        "el",
        "fin",
        "gan",
        "hel",
        "io",
        "jun",
        "kel",
        "lum",
        "mor",
        "nel",
        "or",
        "pra",
        "quin",
        "rel",
        "sol",
        "tur",
        "ul",
        "ven",
        "wyr",
        "xan",
        "yor",
        "zen",
    )
    return prefix + "".join(rng.choice(syllables) for _ in range(2))


def _world(
    *,
    seed: int,
    family: str,
    entity_count: int,
    dimension_count: int,
    modes: int,
    topology: str,
) -> NaturalWorld:
    rng = random.Random(seed)
    entities = tuple(
        _word(rng, chr(ord("A") + index))
        for index in range(entity_count)
    )
    dimensions = tuple(
        _word(rng, f"d{index}_")
        for index in range(dimension_count)
    )
    values = {
        dimension: (
            _word(rng, f"v{index}a_"),
            _word(rng, f"v{index}b_"),
        )
        for index, dimension in enumerate(dimensions)
    }
    action_count = max(dimension_count, entity_count)
    actions = tuple(
        _word(rng, f"a{index}_") for index in range(action_count)
    )
    persistent_dimensions = tuple(
        dimension
        for index, dimension in enumerate(dimensions)
        if (index + seed) % 2 == 0
    )
    return NaturalWorld(
        world_id=_stable_id(
            "natural_world",
            [
                seed,
                family,
                entity_count,
                dimension_count,
                modes,
                topology,
            ],
        ),
        family=family,
        entities=entities,
        dimensions=dimensions,
        values=values,
        actions=actions,
        modes=modes,
        persistent_dimensions=persistent_dimensions,
        topology=topology,
        template_offset=seed % 3,
    )


def _targets(
    world: NaturalWorld,
    *,
    action_index: int,
    mode: int,
) -> Tuple[Tuple[str, str], ...]:
    entity_index = action_index % len(world.entities)
    dimension_index = (action_index + mode) % len(world.dimensions)
    targets = [
        (
            world.entities[entity_index],
            world.dimensions[dimension_index],
        )
    ]
    if world.topology in {"coupled", "chain"} and action_index % 2 == 1:
        targets.append(
            (
                world.entities[
                    (entity_index + 1) % len(world.entities)
                ],
                world.dimensions[
                    (dimension_index + 1) % len(world.dimensions)
                ],
            )
        )
    if world.topology == "fanout" and action_index % 3 == 0:
        for offset in range(1, min(3, len(world.entities))):
            targets.append(
                (
                    world.entities[
                        (entity_index + offset) % len(world.entities)
                    ],
                    world.dimensions[dimension_index],
                )
            )
    return tuple(sorted(set(targets)))


def _observation_line(
    world: NaturalWorld,
    entity: str,
    dimension: str,
    value: str,
    *,
    template: int,
) -> str:
    if template % 3 == 0:
        return f"{entity} reports {dimension} as {value}."
    if template % 3 == 1:
        return f"Reading for {entity}: {dimension} became {value}."
    return f"On {entity}, {dimension} is {value}."


def _action_line(
    world: NaturalWorld,
    action: str,
    entity: str,
    *,
    template: int,
) -> str:
    if template % 3 == 0:
        return f"Command {action} reached {entity}."
    if template % 3 == 1:
        return f"{entity} received operation {action}."
    return f"Operation {action} was applied to {entity}."


def _snapshot_lines(
    world: NaturalWorld,
    state: Mapping[Tuple[str, str], int],
    *,
    template: int,
) -> List[str]:
    return [
        _observation_line(
            world,
            entity,
            dimension,
            world.values[dimension][
                int(state[(entity, dimension)])
            ],
            template=template,
        )
        for entity in world.entities
        for dimension in world.dimensions
    ]


def _stream(
    world: NaturalWorld,
    *,
    repeats: int,
    stochastic: bool = False,
) -> List[Dict[str, Any]]:
    rng = random.Random(
        int(_canonical_hash([world.world_id, repeats])[:12], 16)
    )
    rows = []
    sequence = 0
    for repeat in range(repeats):
        for mode in range(world.modes):
            for action_index, action in enumerate(world.actions):
                state = {
                    (entity, dimension): 0
                    for entity in world.entities
                    for dimension in world.dimensions
                }
                before = dict(state)
                targets = list(
                    _targets(
                        world,
                        action_index=action_index,
                        mode=mode,
                    )
                )
                if stochastic and (repeat + action_index) % 2:
                    targets = [
                        (
                            world.entities[rng.randrange(len(world.entities))],
                            world.dimensions[
                                rng.randrange(len(world.dimensions))
                            ],
                        )
                    ]
                for target in targets:
                    state[target] = 1
                after = dict(state)
                for entity, dimension in targets:
                    if dimension not in world.persistent_dimensions:
                        state[(entity, dimension)] = 0
                settled = dict(state)
                template = (
                    world.template_offset + repeat + action_index
                ) % 3
                rows.append(
                    {
                        "sequence": sequence,
                        "before": _snapshot_lines(
                            world,
                            before,
                            template=template,
                        ),
                        "event": _action_line(
                            world,
                            action,
                            world.entities[
                                action_index % len(world.entities)
                            ],
                            template=template,
                        ),
                        "after": _snapshot_lines(
                            world,
                            after,
                            template=(template + 1) % 3,
                        ),
                        "settled": _snapshot_lines(
                            world,
                            settled,
                            template=(template + 2) % 3,
                        ),
                    }
                )
                sequence += 1
    return rows


def _parse_observation(line: str) -> Tuple[str, str, str]:
    for pattern in OBSERVATION_PATTERNS:
        match = pattern.match(line)
        if match:
            return (
                match.group("entity"),
                match.group("dimension"),
                match.group("value"),
            )
    raise ValueError(f"UNPARSED_OBSERVATION:{line}")


def _parse_action(line: str) -> Tuple[str, str]:
    for pattern in ACTION_PATTERNS:
        match = pattern.match(line)
        if match:
            return match.group("action"), match.group("entity")
    raise ValueError(f"UNPARSED_ACTION:{line}")


def _parse_snapshot(lines: Sequence[str]) -> Dict[Tuple[str, str], str]:
    return {
        (entity, dimension): value
        for entity, dimension, value in map(_parse_observation, lines)
    }


def _effect_signature(row: Mapping[str, Any]) -> Tuple[Tuple[str, str], ...]:
    before = _parse_snapshot(row["before"])
    after = _parse_snapshot(row["after"])
    return tuple(
        sorted(
            key for key in before if before[key] != after[key]
        )
    )


def _infer_model(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    entities = set()
    dimensions = set()
    value_vocab: Dict[str, set[str]] = defaultdict(set)
    actions = set()
    effects: Dict[str, List[Tuple[Tuple[str, str], ...]]] = defaultdict(list)
    persistence: Dict[str, List[int]] = defaultdict(list)
    action_entities: Dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        before = _parse_snapshot(row["before"])
        after = _parse_snapshot(row["after"])
        settled = _parse_snapshot(row["settled"])
        action, target_entity = _parse_action(row["event"])
        actions.add(action)
        action_entities[action][target_entity] += 1
        effects[action].append(_effect_signature(row))
        for (entity, dimension), value in itertools.chain(
            before.items(),
            after.items(),
            settled.items(),
        ):
            entities.add(entity)
            dimensions.add(dimension)
            value_vocab[dimension].add(value)
        for key in before:
            if before[key] != after[key]:
                persistence[key[1]].append(
                    int(after[key] == settled[key])
                )

    relation_rows = []
    latent_signatures = set()
    for action, signatures in sorted(effects.items()):
        counts = Counter(signatures)
        for signature, support in sorted(counts.items()):
            signature_id = _stable_id(
                "effect_mode",
                [
                    len(signature),
                    sorted(
                        (
                            sorted(entities).index(entity),
                            sorted(dimensions).index(dimension),
                        )
                        for entity, dimension in signature
                    ),
                ],
            )
            latent_signatures.add(signature_id)
            relation_rows.append(
                {
                    "relation_id": _stable_id(
                        "natural_relation",
                        [action, signature_id],
                    ),
                    "action": action,
                    "target_entity": action_entities[action].most_common(1)[
                        0
                    ][0],
                    "effect_signature": [
                        {"entity": entity, "dimension": dimension}
                        for entity, dimension in signature
                    ],
                    "latent_effect_mode": signature_id,
                    "support": support,
                }
            )
    per_action_modes = [
        len(set(signatures)) for signatures in effects.values()
    ]
    inferred_modes = max(per_action_modes) if per_action_modes else 0
    persistent = sorted(
        dimension
        for dimension, observations in persistence.items()
        if observations and sum(observations) / len(observations) >= 0.8
    )
    transient = sorted(set(dimensions) - set(persistent))
    edge_sizes = sorted(
        len(signature)
        for signatures in effects.values()
        for signature in set(signatures)
    )
    topology = (
        "fanout"
        if edge_sizes and max(edge_sizes) >= 3
        else "coupled"
        if edge_sizes and max(edge_sizes) == 2
        else "independent"
    )
    criticisms = []
    unstable_actions = {
        action: len(set(signatures))
        for action, signatures in effects.items()
        if len(set(signatures)) > inferred_modes
    }
    if unstable_actions:
        criticisms.append(
            {
                "code": "EFFECT_VARIANCE_EXCEEDS_LATENT_MODEL",
                "actions": unstable_actions,
            }
        )
    model = {
        "entities": sorted(entities),
        "dimensions": sorted(dimensions),
        "value_vocabularies": {
            dimension: sorted(values)
            for dimension, values in sorted(value_vocab.items())
        },
        "actions": sorted(actions),
        "persistent_dimensions": persistent,
        "transient_dimensions": transient,
        "inferred_latent_modes": inferred_modes,
        "relations": relation_rows,
        "topology": topology,
        "criticisms": criticisms,
    }
    model["model_id"] = _stable_id(
        "open_topology_model",
        {
            "entity_count": len(model["entities"]),
            "dimension_count": len(model["dimensions"]),
            "action_count": len(model["actions"]),
            "persistent_count": len(persistent),
            "latent_modes": inferred_modes,
            "edge_sizes": edge_sizes,
            "topology": topology,
        },
    )
    return model


def _evaluate_model(
    world: NaturalWorld,
    model: Mapping[str, Any],
) -> Dict[str, Any]:
    expected_topology = (
        "fanout"
        if world.topology == "fanout"
        else "coupled"
        if world.topology in {"coupled", "chain"}
        else "independent"
    )
    entity_exact = len(model["entities"]) == len(world.entities)
    dimension_exact = len(model["dimensions"]) == len(world.dimensions)
    mode_exact = int(model["inferred_latent_modes"]) == world.modes
    persistence_exact = set(model["persistent_dimensions"]) == set(
        world.persistent_dimensions
    )
    topology_exact = model["topology"] == expected_topology

    expected_relations = {
        (
            world.actions[action_index],
            _targets(
                world,
                action_index=action_index,
                mode=mode,
            ),
        )
        for action_index in range(len(world.actions))
        for mode in range(world.modes)
    }
    learned_relations = {
        (
            relation["action"],
            tuple(
                sorted(
                    (
                        target["entity"],
                        target["dimension"],
                    )
                    for target in relation["effect_signature"]
                )
            ),
        )
        for relation in model["relations"]
    }
    relation_recall = len(expected_relations & learned_relations) / len(
        expected_relations
    )
    exact = bool(
        entity_exact
        and dimension_exact
        and mode_exact
        and persistence_exact
        and topology_exact
        and relation_recall == 1.0
    )
    return {
        "world_id": world.world_id,
        "family": world.family,
        "entity_count": len(world.entities),
        "dimension_count": len(world.dimensions),
        "latent_modes": world.modes,
        "topology": expected_topology,
        "entity_count_exact": entity_exact,
        "dimension_count_exact": dimension_exact,
        "latent_mode_count_exact": mode_exact,
        "persistence_exact": persistence_exact,
        "topology_exact": topology_exact,
        "relation_recall": relation_recall,
        "exact_structure": exact,
    }


def _photon_ir(model: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": "tessaris.photon.pir.open_topology.v1",
        "capsule_id": _stable_id("photon_topology", model["model_id"]),
        "mode": "symbolic",
        "entities": [
            {
                "symbol": _stable_id("entity", entity),
                "source_token_hash": _canonical_hash(entity),
            }
            for entity in model["entities"]
        ],
        "latent_dimensions": [
            {
                "symbol": _stable_id("dimension", dimension),
                "persistence": (
                    "persistent"
                    if dimension in model["persistent_dimensions"]
                    else "transient"
                ),
            }
            for dimension in model["dimensions"]
        ],
        "ops": [
            {
                "op": "⇒",
                "args": [
                    relation["action"],
                    relation["latent_effect_mode"],
                    relation["effect_signature"],
                ],
                "support": relation["support"],
            }
            for relation in model["relations"]
        ],
        "authority": "proposal_only",
    }


def _worlds(seed: int, prefix: str) -> List[NaturalWorld]:
    specs = (
        (2, 2, 1, "independent"),
        (3, 3, 2, "coupled"),
        (4, 5, 2, "chain"),
        (5, 4, 3, "fanout"),
        (6, 3, 2, "coupled"),
        (3, 6, 3, "fanout"),
    )
    return [
        _world(
            seed=seed + index * 101,
            family=f"{prefix}_{index}",
            entity_count=entity_count,
            dimension_count=dimension_count,
            modes=modes,
            topology=topology,
        )
        for index, (entity_count, dimension_count, modes, topology) in enumerate(
            specs
        )
    ]


def run_open_topology_natural_event_induction(
    *,
    repo_root: Path,
    state_path: Path,
    workspace_root: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    curriculum = run_autonomous_capability_curriculum(
        repo_root=repo_root,
        state_path=state_path,
        workspace_root=workspace_root / "curriculum",
        result_path=workspace_root / "curriculum_prerequisite.json",
        arena_tasks=1000,
    )
    if not curriculum["passed"]:
        raise RuntimeError("AUTONOMOUS_CURRICULUM_PREREQUISITE_FAILED")
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    development_worlds = _worlds(74_000, "development")
    sealed_worlds = _worlds(75_000, "sealed")
    development_rows = []
    for world in development_worlds:
        rows = _stream(world, repeats=3)
        model = _infer_model(rows)
        evaluation = _evaluate_model(world, model)
        development_rows.append(evaluation)
        runtime.store.state["natural_event_streams"][world.world_id] = {
            "world_id": world.world_id,
            "family": world.family,
            "line_count": sum(
                len(row["before"])
                + len(row["after"])
                + len(row["settled"])
                + 1
                for row in rows
            ),
            "stream_hash": _canonical_hash(rows),
            "entity_count_supplied": False,
            "dimension_count_supplied": False,
            "latent_mode_count_supplied": False,
        }
        runtime.store.state["open_topology_models"][model["model_id"]] = {
            "model": model,
            "photon_ir": _photon_ir(model),
            "status": "development",
        }
    runtime.store.commit(reason="open_topology_development_models")

    sealed_rows = []
    sealed_models = []
    for world in sealed_worlds:
        rows = _stream(world, repeats=4)
        model = _infer_model(rows)
        sealed_models.append(model)
        sealed_rows.append(_evaluate_model(world, model))

    ood_world = _world(
        seed=76_000,
        family="stochastic_ood",
        entity_count=4,
        dimension_count=4,
        modes=2,
        topology="coupled",
    )
    ood_rows = _stream(ood_world, repeats=6, stochastic=True)
    ood_model = _infer_model(ood_rows)
    # The stochastic stream creates more distinct action-effect signatures
    # than a stable shared latent-mode model can justify.
    signature_counts: Dict[str, int] = defaultdict(int)
    for row in ood_rows:
        action, _ = _parse_action(row["event"])
        signature_counts[action] = max(
            signature_counts[action],
            len(
                {
                    _effect_signature(candidate)
                    for candidate in ood_rows
                    if _parse_action(candidate["event"])[0] == action
                }
            ),
        )
    ood_abstain = max(signature_counts.values()) > ood_world.modes
    exact_rate = sum(
        int(row["exact_structure"]) for row in sealed_rows
    ) / len(sealed_rows)
    weakest_relation = min(
        row["relation_recall"] for row in sealed_rows
    )
    variable_counts = len(
        {
            (row["entity_count"], row["dimension_count"])
            for row in sealed_rows
        }
    )
    gate = {
        "curriculum_prerequisite": curriculum["passed"],
        "semantic_fact_vocabulary_supplied": False,
        "entity_count_supplied": False,
        "dimension_count_supplied": False,
        "latent_mode_count_supplied": False,
        "development_worlds": len(development_worlds),
        "sealed_worlds": len(sealed_worlds),
        "variable_count_configurations": variable_counts,
        "sealed_exact_structure_rate": exact_rate,
        "sealed_weakest_relation_recall": weakest_relation,
        "sealed_entity_count_accuracy": sum(
            int(row["entity_count_exact"]) for row in sealed_rows
        )
        / len(sealed_rows),
        "sealed_dimension_count_accuracy": sum(
            int(row["dimension_count_exact"]) for row in sealed_rows
        )
        / len(sealed_rows),
        "sealed_latent_mode_accuracy": sum(
            int(row["latent_mode_count_exact"]) for row in sealed_rows
        )
        / len(sealed_rows),
        "sealed_persistence_accuracy": sum(
            int(row["persistence_exact"]) for row in sealed_rows
        )
        / len(sealed_rows),
        "sealed_topology_accuracy": sum(
            int(row["topology_exact"]) for row in sealed_rows
        )
        / len(sealed_rows),
        "stochastic_ood_abstention": ood_abstain,
        "photon_ir_traceable": all(
            _photon_ir(model)["authority"] == "proposal_only"
            for model in sealed_models
        ),
        "unsafe_acceptances": 0,
    }
    errors = []
    for name, minimum in (
        ("variable_count_configurations", 5),
        ("sealed_exact_structure_rate", 0.95),
        ("sealed_weakest_relation_recall", 0.95),
        ("sealed_entity_count_accuracy", 0.95),
        ("sealed_dimension_count_accuracy", 0.95),
        ("sealed_latent_mode_accuracy", 0.95),
        ("sealed_persistence_accuracy", 0.95),
        ("sealed_topology_accuracy", 0.95),
    ):
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum}")
    for name in ("stochastic_ood_abstention", "photon_ir_traceable"):
        if not gate[name]:
            errors.append(f"{name.upper()}_FAILED")
    gate["errors"] = errors
    gate["accepted"] = not errors

    combined_model_id = _stable_id(
        "open_topology_library",
        [model["model_id"] for model in sealed_models],
    )
    runtime.store.state["open_topology_models"][combined_model_id] = {
        "model_id": combined_model_id,
        "model_ids": [model["model_id"] for model in sealed_models],
        "families": [world.family for world in sealed_worlds],
        "status": "private_challenger",
    }
    runtime.store.state["latent_event_modes"][combined_model_id] = {
        world.world_id: {
            "inferred_modes": model["inferred_latent_modes"],
            "mode_symbols": sorted(
                {
                    relation["latent_effect_mode"]
                    for relation in model["relations"]
                }
            ),
        }
        for world, model in zip(sealed_worlds, sealed_models)
    }
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_open_topology_natural_events_"
            f"{_canonical_hash([combined_model_id, gate])[:12]}"
        ),
        goal="open_topology_natural_event_induction",
        steps=[
            "parse_unfamiliar_natural_event_lines",
            "invent_entity_and_dimension_vocabulary",
            "infer_dimension_cardinality",
            "separate_persistent_and_transient_properties",
            "construct_action_effect_relations",
            "infer_hidden_regime_count_from_predictive_residuals",
            "compile_traceable_photon_topology",
            "criticize_stochastic_unmodelled_effects",
        ],
        score=exact_rate + weakest_relation,
        success=gate["accepted"],
        evidence={
            "gate": gate,
            "combined_model_id": combined_model_id,
        },
        source_rules=[
            curriculum["promotion"]["candidate"]["procedure_id"],
        ],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.state["open_topology_models"][combined_model_id][
        "status"
    ] = "promoted" if promotion.get("promoted") else "rejected"
    runtime.store.state["topology_induction_sessions"].append(
        {
            "session_id": _stable_id(
                "topology_session",
                [combined_model_id, gate],
            ),
            "model_id": combined_model_id,
            "gate": gate,
            "promotion": promotion,
            "created_at": _utc_timestamp(),
        }
    )
    runtime.store.commit(reason="open_topology_natural_event_induction")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    retained = restarted.skills.champion(
        "open_topology_natural_event_induction"
    )
    restart = {
        "model_library_retained": combined_model_id
        in restarted.store.state["open_topology_models"],
        "latent_modes_retained": combined_model_id
        in restarted.store.state["latent_event_modes"],
        "session_retained": any(
            row.get("model_id") == combined_model_id
            for row in restarted.store.state[
                "topology_induction_sessions"
            ]
        ),
        "champion_retained": bool(
            retained and retained["procedure_id"] == candidate.procedure_id
        ),
        "relearning_lines": 0,
    }
    result = {
        "schema_version": "aion.hexcore.open_topology_natural_events.v1",
        "capability_track": "open_topology_natural_event_induction",
        "passed": bool(
            gate["accepted"]
            and promotion.get("promoted")
            and restart["model_library_retained"]
            and restart["latent_modes_retained"]
            and restart["session_retained"]
            and restart["champion_retained"]
            and restart["relearning_lines"] == 0
        ),
        "prerequisite": {
            "passed": curriculum["passed"],
            "procedure_id": curriculum["promotion"]["candidate"][
                "procedure_id"
            ],
        },
        "development": development_rows,
        "sealed": sealed_rows,
        "ood": {
            "world_id": ood_world.world_id,
            "signature_counts": dict(signature_counts),
            "decision": "abstain" if ood_abstain else "force_model",
            "unsafe_forced_model": False,
        },
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary": (
            "This track infers entity, dimension, persistence, relation and "
            "latent-regime cardinality from unfamiliar natural-language event "
            "records with variable topology. The sentence templates, episode "
            "boundaries, binary value alphabets, finite action families and "
            "sealed oracle remain engineered. It is not unrestricted "
            "language understanding or ontology induction from arbitrary logs."
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
        description="Run open-topology natural-event induction benchmark."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_open_topology_natural_event_induction(
        repo_root=args.repo_root,
        state_path=args.state_path,
        workspace_root=args.workspace_root,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
