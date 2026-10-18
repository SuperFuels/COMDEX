from __future__ import annotations

import argparse
import json
import math
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


EXPLICIT_READING = re.compile(
    r"^At (?P<time>\d+), (?P<entity>[A-Z][A-Za-z0-9_-]+) measured "
    r"(?P<dimension>[a-z][a-z0-9_-]+) at (?P<value>-?\d+(?:\.\d+)?)\.$"
)
ENTITY_COREFERENCE = re.compile(
    r"^At (?P<time>\d+), that unit measured "
    r"(?P<dimension>[a-z][a-z0-9_-]+) at (?P<value>-?\d+(?:\.\d+)?)\.$"
)
DIMENSION_COREFERENCE = re.compile(
    r"^At (?P<time>\d+), (?P<entity>[A-Z][A-Za-z0-9_-]+) kept "
    r"the same channel at (?P<value>-?\d+(?:\.\d+)?)\.$"
)
DUPLICATE_COREFERENCE = re.compile(
    r"^At (?P<time>\d+), it still held there at "
    r"(?P<value>-?\d+(?:\.\d+)?)\.$"
)
ACTION_RE = re.compile(
    r"^At (?P<time>\d+), operator (?P<action>[a-z][a-z0-9_-]+) "
    r"was applied to (?P<entity>[A-Z][A-Za-z0-9_-]+)\.$"
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "continuous_natural_world_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}_{_canonical_hash(value)[:16]}"


@dataclass(frozen=True)
class ContinuousWorld:
    world_id: str
    family: str
    entities: Tuple[str, ...]
    dimensions: Tuple[str, ...]
    actions: Tuple[str, ...]
    persistent_dimensions: Tuple[str, ...]
    modes: int
    topology: str
    coefficients: Mapping[Tuple[int, int], Tuple[Tuple[int, int, float], ...]]
    nonlinear: bool = False


def _word(rng: random.Random, prefix: str) -> str:
    parts = (
        "ara",
        "bel",
        "cor",
        "dun",
        "evi",
        "fal",
        "gan",
        "hel",
        "iri",
        "jor",
        "kel",
        "lum",
        "mor",
        "nor",
        "ora",
        "pra",
        "quin",
        "rel",
        "sol",
        "tor",
        "uvi",
        "ven",
        "wyr",
        "xan",
        "yor",
        "zen",
    )
    return prefix + rng.choice(parts) + rng.choice(parts)


def _targets(
    *,
    entity_count: int,
    dimension_count: int,
    action_index: int,
    mode: int,
    topology: str,
) -> Tuple[Tuple[int, int], ...]:
    entity = action_index % entity_count
    dimension = (action_index + mode) % dimension_count
    targets = [(entity, dimension)]
    if topology in {"coupled", "chain"} and action_index % 2:
        targets.append(
            (
                (entity + 1) % entity_count,
                (dimension + 1) % dimension_count,
            )
        )
    if topology == "fanout" and action_index % 3 == 0:
        for offset in range(1, min(3, entity_count)):
            targets.append(((entity + offset) % entity_count, dimension))
    return tuple(sorted(set(targets)))


def _world(
    *,
    seed: int,
    family: str,
    entity_count: int,
    dimension_count: int,
    modes: int,
    topology: str,
    nonlinear: bool = False,
) -> ContinuousWorld:
    rng = random.Random(seed)
    entities = tuple(
        _word(rng, chr(ord("A") + index))
        for index in range(entity_count)
    )
    dimensions = tuple(
        _word(rng, f"m{index}_") for index in range(dimension_count)
    )
    actions = tuple(
        _word(rng, f"op{index}_")
        for index in range(max(entity_count, dimension_count))
    )
    persistent = tuple(
        dimension
        for index, dimension in enumerate(dimensions)
        if (index + seed) % 2 == 0
    )
    coefficients = {}
    for action_index in range(len(actions)):
        for mode in range(modes):
            relations = []
            for target_index, (entity, dimension) in enumerate(
                _targets(
                    entity_count=entity_count,
                    dimension_count=dimension_count,
                    action_index=action_index,
                    mode=mode,
                    topology=topology,
                )
            ):
                magnitude = (
                    0.65
                    + 0.19 * mode
                    + 0.07 * (action_index % 4)
                    + 0.04 * target_index
                )
                sign = -1.0 if (action_index + target_index) % 3 == 0 else 1.0
                relations.append((entity, dimension, sign * magnitude))
            coefficients[(action_index, mode)] = tuple(relations)
    return ContinuousWorld(
        world_id=_stable_id(
            "continuous_world",
            [
                seed,
                family,
                entity_count,
                dimension_count,
                modes,
                topology,
                nonlinear,
            ],
        ),
        family=family,
        entities=entities,
        dimensions=dimensions,
        actions=actions,
        persistent_dimensions=persistent,
        modes=modes,
        topology=topology,
        coefficients=coefficients,
        nonlinear=nonlinear,
    )


def _reading_lines(
    *,
    timestamp: int,
    state: Mapping[Tuple[str, str], float],
    rng: random.Random,
    required: set[Tuple[str, str]],
    missing_rate: float,
) -> List[Dict[str, Any]]:
    keys = sorted(state)
    rows = []
    last_entity: str | None = None
    last_dimension: str | None = None
    for index, (entity, dimension) in enumerate(keys):
        if (entity, dimension) not in required and rng.random() < missing_rate:
            continue
        value = state[(entity, dimension)] + rng.uniform(-0.008, 0.008)
        style = rng.randrange(3)
        if style == 1 and last_entity == entity:
            text = (
                f"At {timestamp}, that unit measured {dimension} "
                f"at {value:.3f}."
            )
        elif style == 2 and last_dimension == dimension:
            text = (
                f"At {timestamp}, {entity} kept the same channel "
                f"at {value:.3f}."
            )
        else:
            text = (
                f"At {timestamp}, {entity} measured {dimension} "
                f"at {value:.3f}."
            )
        rows.append({"timestamp": timestamp, "text": text})
        last_entity, last_dimension = entity, dimension
        if index % 11 == 0:
            rows.append(
                {
                    "timestamp": timestamp,
                    "text": (
                        f"At {timestamp}, it still held there at "
                        f"{value:.3f}."
                    ),
                }
            )
    return rows


def _stream(
    world: ContinuousWorld,
    *,
    repeats: int,
    seed: int,
    missing_rate: float = 0.08,
    coefficient_scale: float = 1.0,
    change_after: int | None = None,
    alternating_scale: bool = False,
) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    state = {
        (entity, dimension): rng.uniform(-0.15, 0.15)
        for entity in world.entities
        for dimension in world.dimensions
    }
    rows: List[Dict[str, Any]] = []
    timestamp = 0
    rows.extend(
        _reading_lines(
            timestamp=timestamp,
            state=state,
            rng=rng,
            required=set(),
            missing_rate=0.0,
        )
    )
    episode_index = 0
    for repeat in range(repeats):
        for mode in range(world.modes):
            for action_index, action in enumerate(world.actions):
                before = dict(state)
                raw_relations = world.coefficients[(action_index, mode)]
                relations = []
                if alternating_scale:
                    active_scale = (
                        coefficient_scale if episode_index % 2 else 1.0
                    )
                else:
                    active_scale = (
                        coefficient_scale
                        if change_after is not None
                        and episode_index >= change_after
                        else 1.0
                    )
                for entity_index, dimension_index, coefficient in raw_relations:
                    key = (
                        world.entities[entity_index],
                        world.dimensions[dimension_index],
                    )
                    delta = coefficient * active_scale
                    if world.nonlinear:
                        delta *= 0.35 + abs(before[key]) ** 2
                    relations.append((key, delta))
                timestamp += 1
                rows.append(
                    {
                        "timestamp": timestamp,
                        "text": (
                            f"At {timestamp}, operator {action} was applied to "
                            f"{world.entities[action_index % len(world.entities)]}."
                        ),
                    }
                )
                for key, delta in relations:
                    state[key] += delta
                timestamp += 1
                target_keys = {key for key, _ in relations}
                rows.extend(
                    _reading_lines(
                        timestamp=timestamp,
                        state=state,
                        rng=rng,
                        required=target_keys,
                        missing_rate=missing_rate,
                    )
                )
                for key, _ in relations:
                    if key[1] not in world.persistent_dimensions:
                        state[key] = before[key]
                timestamp += 1
                rows.extend(
                    _reading_lines(
                        timestamp=timestamp,
                        state=state,
                        rng=rng,
                        required=target_keys,
                        missing_rate=missing_rate,
                    )
                )
                episode_index += 1
    return rows


def _parse_records(
    records: Sequence[Mapping[str, Any]],
) -> Tuple[Dict[int, Dict[Tuple[str, str], float]], List[Dict[str, Any]], Dict[str, Any]]:
    observations: Dict[int, Dict[Tuple[str, str], float]] = defaultdict(dict)
    actions = []
    last_entity: str | None = None
    last_dimension: str | None = None
    coreference_records = 0
    for record in sorted(records, key=lambda row: int(row["timestamp"])):
        text = str(record["text"])
        match = ACTION_RE.match(text)
        if match:
            actions.append(
                {
                    "timestamp": int(match.group("time")),
                    "action": match.group("action"),
                    "target_entity": match.group("entity"),
                }
            )
            last_entity = match.group("entity")
            continue
        match = EXPLICIT_READING.match(text)
        if match:
            timestamp = int(match.group("time"))
            last_entity = match.group("entity")
            last_dimension = match.group("dimension")
            observations[timestamp][(last_entity, last_dimension)] = float(
                match.group("value")
            )
            continue
        match = ENTITY_COREFERENCE.match(text)
        if match and last_entity is not None:
            timestamp = int(match.group("time"))
            last_dimension = match.group("dimension")
            observations[timestamp][(last_entity, last_dimension)] = float(
                match.group("value")
            )
            coreference_records += 1
            continue
        match = DIMENSION_COREFERENCE.match(text)
        if match and last_dimension is not None:
            timestamp = int(match.group("time"))
            last_entity = match.group("entity")
            observations[timestamp][(last_entity, last_dimension)] = float(
                match.group("value")
            )
            coreference_records += 1
            continue
        match = DUPLICATE_COREFERENCE.match(text)
        if match and last_entity is not None and last_dimension is not None:
            timestamp = int(match.group("time"))
            observations[timestamp][(last_entity, last_dimension)] = float(
                match.group("value")
            )
            coreference_records += 1
            continue
        raise ValueError(f"UNPARSED_NATURAL_EVENT:{text}")
    return observations, actions, {
        "coreference_records": coreference_records,
        "observation_times": len(observations),
        "actions": len(actions),
    }


def _episodes(records: Sequence[Mapping[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    observations, actions, parse_metrics = _parse_records(records)
    timestamps = sorted(observations)
    episodes = []
    last_known: Dict[Tuple[str, str], float] = {}
    time_to_state: Dict[int, Dict[Tuple[str, str], float]] = {}
    for timestamp in timestamps:
        last_known.update(observations[timestamp])
        time_to_state[timestamp] = dict(last_known)
    for action in actions:
        timestamp = int(action["timestamp"])
        before_times = [item for item in timestamps if item < timestamp]
        after_times = [item for item in timestamps if item > timestamp]
        if not before_times or len(after_times) < 2:
            continue
        before_time = max(before_times)
        immediate_time = after_times[0]
        settled_time = after_times[1]
        episodes.append(
            {
                **action,
                "before": time_to_state[before_time],
                "immediate": time_to_state[immediate_time],
                "settled": time_to_state[settled_time],
            }
        )
    return episodes, parse_metrics


def _signature(
    episode: Mapping[str, Any],
    *,
    threshold: float = 0.15,
) -> Tuple[Tuple[str, str], ...]:
    before = episode["before"]
    immediate = episode["immediate"]
    return tuple(
        sorted(
            key
            for key in before.keys() & immediate.keys()
            if abs(immediate[key] - before[key]) >= threshold
        )
    )


def _infer(records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    episodes, parse_metrics = _episodes(records)
    all_keys = set()
    effects: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    persistence_votes: Dict[str, List[bool]] = defaultdict(list)
    for episode in episodes:
        all_keys.update(episode["before"])
        all_keys.update(episode["immediate"])
        all_keys.update(episode["settled"])
        signature = _signature(episode)
        coefficients = {}
        for key in signature:
            delta = episode["immediate"][key] - episode["before"][key]
            coefficients[key] = delta
            settled_delta = episode["settled"][key] - episode["before"][key]
            persistence_votes[key[1]].append(
                abs(settled_delta - delta) <= max(0.05, abs(delta) * 0.12)
            )
        effects[episode["action"]].append(
            {
                "signature": signature,
                "coefficients": coefficients,
            }
        )
    entities = sorted({key[0] for key in all_keys})
    dimensions = sorted({key[1] for key in all_keys})
    relations = []
    unstable = []
    per_action_modes = []
    for action, rows in sorted(effects.items()):
        grouped: Dict[Tuple[Tuple[str, str], ...], List[Mapping[Tuple[str, str], float]]] = defaultdict(list)
        for row in rows:
            grouped[row["signature"]].append(row["coefficients"])
        per_action_modes.append(len(grouped))
        # Dictionary insertion order preserves the first observed phase of the
        # recurring hidden-regime cycle; alphabetic signature order would erase
        # that temporal information and damage prospective prediction.
        for mode_index, (signature, coefficient_rows) in enumerate(
            grouped.items()
        ):
            coefficients = {}
            deviations = []
            for key in signature:
                values = [float(row[key]) for row in coefficient_rows if key in row]
                mean = sum(values) / len(values)
                variance = sum((value - mean) ** 2 for value in values) / len(values)
                coefficients[f"{key[0]}::{key[1]}"] = mean
                deviations.append(math.sqrt(variance) / max(abs(mean), 0.05))
            maximum_cv = max(deviations, default=0.0)
            if maximum_cv > 0.22:
                unstable.append(
                    {
                        "action": action,
                        "mode": mode_index,
                        "coefficient_cv": maximum_cv,
                    }
                )
            relations.append(
                {
                    "action": action,
                    "mode": mode_index,
                    "signature": [list(key) for key in signature],
                    "coefficients": coefficients,
                    "support": len(coefficient_rows),
                    "maximum_coefficient_cv": maximum_cv,
                }
            )
    inferred_modes = max(per_action_modes, default=0)
    edge_sizes = [len(row["signature"]) for row in relations]
    topology = (
        "fanout"
        if edge_sizes and max(edge_sizes) >= 3
        else "coupled"
        if edge_sizes and max(edge_sizes) == 2
        else "independent"
    )
    persistent = sorted(
        dimension
        for dimension, votes in persistence_votes.items()
        if votes and sum(votes) / len(votes) >= 0.8
    )
    model = {
        "entities": entities,
        "dimensions": dimensions,
        "actions": sorted(effects),
        "persistent_dimensions": persistent,
        "transient_dimensions": sorted(set(dimensions) - set(persistent)),
        "inferred_modes": inferred_modes,
        "topology": topology,
        "relations": relations,
        "criticisms": (
            [
                {
                    "code": "NON_STATIONARY_OR_NONLINEAR_EFFECTS",
                    "unstable_modes": unstable,
                }
            ]
            if unstable
            else []
        ),
        "parse_metrics": parse_metrics,
    }
    model["model_id"] = _stable_id(
        "continuous_model",
        {
            "entities": len(entities),
            "dimensions": len(dimensions),
            "actions": len(effects),
            "modes": inferred_modes,
            "topology": topology,
            "persistent": len(persistent),
            "relations": [
                (row["action"], row["mode"], row["signature"])
                for row in relations
            ],
        },
    )
    return model


def _expected_topology(world: ContinuousWorld) -> str:
    if world.topology == "fanout":
        return "fanout"
    if world.topology in {"coupled", "chain"}:
        return "coupled"
    return "independent"


def _relation_map(model: Mapping[str, Any]) -> Dict[str, List[Mapping[str, Any]]]:
    result: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for relation in model["relations"]:
        result[str(relation["action"])].append(relation)
    for rows in result.values():
        rows.sort(key=lambda row: int(row["mode"]))
    return result


def _evaluate(
    world: ContinuousWorld,
    model: Mapping[str, Any],
    *,
    heldout_records: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    heldout_episodes, _ = _episodes(heldout_records)
    relation_map = _relation_map(model)
    action_counts: Counter[str] = Counter()
    predictions = []
    coefficient_errors = []
    for episode in heldout_episodes:
        action = str(episode["action"])
        options = relation_map.get(action, [])
        if not options:
            predictions.append(False)
            continue
        option = options[action_counts[action] % len(options)]
        action_counts[action] += 1
        observed_signature = _signature(episode)
        predicted_signature = tuple(tuple(key) for key in option["signature"])
        correct = predicted_signature == observed_signature
        predictions.append(correct)
        if correct:
            for key in observed_signature:
                key_text = f"{key[0]}::{key[1]}"
                predicted = float(option["coefficients"][key_text])
                observed = (
                    episode["immediate"][key] - episode["before"][key]
                )
                coefficient_errors.append(abs(predicted - observed))
    expected_relations = {
        (
            world.actions[action_index],
            tuple(
                sorted(
                    (
                        world.entities[entity],
                        world.dimensions[dimension],
                    )
                    for entity, dimension, _ in world.coefficients[
                        (action_index, mode)
                    ]
                )
            ),
        )
        for action_index in range(len(world.actions))
        for mode in range(world.modes)
    }
    learned_relations = {
        (
            row["action"],
            tuple(tuple(key) for key in row["signature"]),
        )
        for row in model["relations"]
    }
    relation_recall = len(expected_relations & learned_relations) / len(
        expected_relations
    )
    coefficient_mae = (
        sum(coefficient_errors) / len(coefficient_errors)
        if coefficient_errors
        else float("inf")
    )
    prediction_accuracy = sum(predictions) / max(1, len(predictions))
    exact_structure = bool(
        len(model["entities"]) == len(world.entities)
        and len(model["dimensions"]) == len(world.dimensions)
        and int(model["inferred_modes"]) == world.modes
        and model["topology"] == _expected_topology(world)
        and set(model["persistent_dimensions"])
        == set(world.persistent_dimensions)
        and relation_recall == 1.0
    )
    return {
        "world_id": world.world_id,
        "family": world.family,
        "exact_structure": exact_structure,
        "entity_count_exact": len(model["entities"]) == len(world.entities),
        "dimension_count_exact": len(model["dimensions"]) == len(world.dimensions),
        "mode_count_exact": int(model["inferred_modes"]) == world.modes,
        "topology_exact": model["topology"] == _expected_topology(world),
        "persistence_exact": set(model["persistent_dimensions"])
        == set(world.persistent_dimensions),
        "relation_recall": relation_recall,
        "heldout_prediction_accuracy": prediction_accuracy,
        "coefficient_mae": coefficient_mae,
        "criticized": bool(model["criticisms"]),
        "coreference_records": int(
            model["parse_metrics"]["coreference_records"]
        ),
    }


def _photon_ir(model: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": "tessaris.photon.pir.continuous_world.v1",
        "capsule_id": _stable_id("photon_continuous", model["model_id"]),
        "mode": "symbolic_numeric",
        "state_dimensions": [
            {
                "symbol": _stable_id("dimension", dimension),
                "persistence": (
                    "persistent"
                    if dimension in model["persistent_dimensions"]
                    else "transient"
                ),
                "numeric_type": "continuous",
            }
            for dimension in model["dimensions"]
        ],
        "ops": [
            {
                "op": "⇒",
                "action": relation["action"],
                "latent_mode": relation["mode"],
                "targets": relation["signature"],
                "coefficients": relation["coefficients"],
                "support": relation["support"],
            }
            for relation in model["relations"]
        ],
        "criticisms": model["criticisms"],
        "authority": "proposal_only",
    }


def _cohort(seed: int, prefix: str) -> List[ContinuousWorld]:
    specs = (
        (2, 2, 1, "independent"),
        (3, 3, 2, "coupled"),
        (4, 4, 2, "chain"),
        (5, 3, 2, "fanout"),
        (3, 5, 3, "coupled"),
        (6, 4, 3, "fanout"),
        (4, 6, 2, "chain"),
        (5, 5, 3, "fanout"),
    )
    return [
        _world(
            seed=seed + index * 97,
            family=f"{prefix}_{index}",
            entity_count=entities,
            dimension_count=dimensions,
            modes=modes,
            topology=topology,
        )
        for index, (entities, dimensions, modes, topology) in enumerate(specs)
    ]


def _dependency(repo_root: Path) -> Dict[str, Any]:
    path = repo_root / "results" / "hexcore_open_topology_natural_events.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload.get("passed"):
        raise RuntimeError("OPEN_TOPOLOGY_DEPENDENCY_NOT_PROMOTED")
    return {
        "path": str(path),
        "result_hash": _canonical_hash(payload),
        "procedure_id": payload["promotion"]["decision"]["champion_id"],
        "passed": True,
    }


def run_continuous_natural_world_learning(
    *,
    repo_root: Path,
    state_path: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    dependency = _dependency(repo_root.resolve())
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    development_worlds = _cohort(81_000, "development")
    sealed_worlds = _cohort(82_000, "sealed")
    development = []
    for index, world in enumerate(development_worlds):
        training = _stream(
            world,
            repeats=4,
            seed=83_000 + index,
        )
        heldout = _stream(
            world,
            repeats=2,
            seed=84_000 + index,
        )
        model = _infer(training)
        development.append(
            _evaluate(world, model, heldout_records=heldout)
        )
    sealed = []
    sealed_models = []
    total_coreferences = 0
    for index, world in enumerate(sealed_worlds):
        training = _stream(
            world,
            repeats=5,
            seed=85_000 + index,
        )
        heldout = _stream(
            world,
            repeats=3,
            seed=86_000 + index,
        )
        model = _infer(training)
        evaluation = _evaluate(
            world,
            model,
            heldout_records=heldout,
        )
        sealed.append(evaluation)
        sealed_models.append(model)
        total_coreferences += evaluation["coreference_records"]
        runtime.store.state["continuous_event_streams"][world.world_id] = {
            "world_id": world.world_id,
            "family": world.family,
            "training_hash": _canonical_hash(training),
            "heldout_hash": _canonical_hash(heldout),
            "semantic_vocabulary_supplied": False,
            "state_dimension_count_supplied": False,
            "continuous_values": True,
        }
        runtime.store.state["continuous_world_models"][model["model_id"]] = {
            "model": model,
            "photon_ir": _photon_ir(model),
            "status": "sealed_challenger",
        }

    nonlinear_world = _world(
        seed=87_000,
        family="nonlinear_ood",
        entity_count=4,
        dimension_count=4,
        modes=2,
        topology="coupled",
        nonlinear=True,
    )
    nonlinear_training = _stream(
        nonlinear_world,
        repeats=6,
        seed=87_100,
    )
    nonlinear_model = _infer(nonlinear_training)
    nonlinear_criticized = bool(nonlinear_model["criticisms"])
    criticism = {
        "world_id": nonlinear_world.world_id,
        "decision": "abstain" if nonlinear_criticized else "force_model",
        "criticisms": nonlinear_model["criticisms"],
        "unsafe_acceptance": not nonlinear_criticized,
    }
    runtime.store.state["model_criticism_records"].append(criticism)

    gate = {
        "dependency_promoted": dependency["passed"],
        "semantic_fact_vocabulary_supplied": False,
        "entity_count_supplied": False,
        "dimension_count_supplied": False,
        "continuous_values": True,
        "coreference_records_resolved": total_coreferences,
        "missing_noncritical_observations": True,
        "development_worlds": len(development),
        "sealed_worlds": len(sealed),
        "sealed_exact_structure_rate": sum(
            int(row["exact_structure"]) for row in sealed
        )
        / len(sealed),
        "sealed_weakest_relation_recall": min(
            row["relation_recall"] for row in sealed
        ),
        "sealed_mean_prediction_accuracy": sum(
            row["heldout_prediction_accuracy"] for row in sealed
        )
        / len(sealed),
        "sealed_weakest_prediction_accuracy": min(
            row["heldout_prediction_accuracy"] for row in sealed
        ),
        "sealed_mean_coefficient_mae": sum(
            row["coefficient_mae"] for row in sealed
        )
        / len(sealed),
        "nonlinear_ood_abstention": nonlinear_criticized,
        "unsafe_acceptances": int(not nonlinear_criticized),
    }
    errors = []
    if gate["sealed_exact_structure_rate"] < 0.90:
        errors.append("STRUCTURE_RECOVERY_BELOW_90_PERCENT")
    if gate["sealed_weakest_relation_recall"] < 0.90:
        errors.append("RELATION_RECALL_BELOW_90_PERCENT")
    if gate["sealed_mean_prediction_accuracy"] < 0.90:
        errors.append("MEAN_PREDICTION_BELOW_90_PERCENT")
    if gate["sealed_weakest_prediction_accuracy"] < 0.80:
        errors.append("WORST_WORLD_PREDICTION_BELOW_80_PERCENT")
    if gate["sealed_mean_coefficient_mae"] > 0.06:
        errors.append("COEFFICIENT_ERROR_ABOVE_006")
    if not nonlinear_criticized:
        errors.append("NONLINEAR_OOD_NOT_CRITICIZED")
    gate["accepted"] = not errors
    gate["errors"] = errors

    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_continuous_natural_world_"
            + _canonical_hash(
                {
                    "parent": dependency["procedure_id"],
                    "gate": gate,
                }
            )[:12]
        ),
        goal="continuous_natural_world_learning",
        steps=[
            "parse_timestamped_natural_records",
            "resolve_local_entity_and_dimension_coreference",
            "invent_continuous_state_dimensions",
            "infer_persistent_and_transient_effects",
            "infer_latent_regime_count_and_topology",
            "estimate_causal_coefficients",
            "predict_withheld_future_events",
            "criticize_nonstationary_or_nonlinear_effects",
            "compile_traceable_photon_world_model",
        ],
        score=(
            gate["sealed_mean_prediction_accuracy"]
            + gate["sealed_exact_structure_rate"]
            - gate["sealed_mean_coefficient_mae"]
        ),
        success=gate["accepted"],
        evidence={
            "dependency": dependency,
            "gate": gate,
        },
        source_rules=[dependency["procedure_id"]],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.state["topology_induction_sessions"].append(
        {
            "session_id": _stable_id(
                "continuous_induction_session",
                candidate.procedure_id,
            ),
            "procedure_id": candidate.procedure_id,
            "sealed_worlds": [row["world_id"] for row in sealed],
            "gate": gate,
        }
    )
    runtime.store.commit(reason="continuous_natural_world_promotion")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path.resolve(),
        authority_provider=_allow,
    )
    restart = {
        "champion_retained": restarted.store.state["champions"].get(
            "continuous_natural_world_learning"
        )
        == candidate.procedure_id,
        "models_retained": all(
            model["model_id"]
            in restarted.store.state["continuous_world_models"]
            for model in sealed_models
        ),
        "criticism_retained": any(
            row.get("world_id") == nonlinear_world.world_id
            for row in restarted.store.state["model_criticism_records"]
        ),
        "relearning_records": 0,
    }
    passed = bool(
        gate["accepted"]
        and (
            promotion.get("promoted")
            or promotion.get("champion_id") == candidate.procedure_id
        )
        and restart["champion_retained"]
        and restart["models_retained"]
        and restart["criticism_retained"]
        and restart["relearning_records"] == 0
    )
    result = {
        "schema_version": "aion.hexcore.continuous_natural_world.v1",
        "capability_track": "continuous_coreferential_world_learning",
        "passed": passed,
        "dependency": dependency,
        "development": development,
        "sealed": sealed,
        "nonlinear_ood": criticism,
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary": (
            "AION infers variable-size continuous causal state from timestamped "
            "natural records containing local coreference, missing non-critical "
            "readings and latent regimes, and predicts withheld future effects. "
            "The record grammar, local coreference scope, finite action family, "
            "piecewise-stationary assumption and simulator authority remain "
            "engineered; this is not arbitrary language or unrestricted physics."
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
        description="Run continuous natural-world induction."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_continuous_natural_world_learning(
        repo_root=args.repo_root,
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
