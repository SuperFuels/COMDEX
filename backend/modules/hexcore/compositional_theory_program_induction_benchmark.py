from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


Point = Tuple[int, ...]
NOISE = 0.02
FAMILY_ORDER = ("parameter", "exception", "latent", "operator")
DOMAINS = (
    "adaptive battery foundry",
    "distributed habitat control",
    "coastal nutrient exchange",
    "autonomous telescope network",
    "emergency materials lattice",
    "subsurface microbial survey",
)
EXTERNAL_DOMAINS = (
    "external cryogenic relay",
    "external forest carbon exchange",
)


@dataclass(frozen=True, order=True)
class Program:
    family: str
    threshold: int
    primary: int = -1
    secondary: int = -1
    trigger: int = 2
    width: int = -1

    def predict(self, point: Point) -> bool:
        total = sum(point)
        if self.family == "parameter":
            return total >= self.threshold
        if self.family == "exception":
            return (
                total >= self.threshold
                and point[self.primary] != self.trigger
            )
        if self.family == "latent":
            latent = (
                point[self.primary] >= 1
                and point[self.secondary] >= 1
            )
            remainder = sum(
                value
                for index, value in enumerate(point)
                if index not in {self.primary, self.secondary}
            )
            return latent and remainder >= self.threshold
        if self.family == "operator":
            return (
                max(point) - min(point) <= self.width
                and total >= self.threshold
            )
        raise ValueError(self.family)

    @property
    def complexity(self) -> int:
        return {
            "parameter": 1,
            "exception": 2,
            "operator": 2,
            "latent": 3,
        }[self.family]

    @property
    def revision_kind(self) -> str:
        return {
            "parameter": "PARAMETER_REVISION",
            "exception": "CONTEXTUAL_EXCEPTION_INVENTION",
            "latent": "HIDDEN_INTERMEDIATE_PREDICATE",
            "operator": "NEW_OPERATOR_INVENTION",
        }[self.family]

    @property
    def program_id(self) -> str:
        return "theory_program_" + _canonical_hash(asdict(self))[:12]


@dataclass(frozen=True)
class ProgramWorld:
    world_id: str
    domain: str
    symbols: Tuple[str, ...]
    truth: Program | None
    seed: int
    out_of_grammar: bool = False

    @property
    def arity(self) -> int:
        return len(self.symbols)

    @property
    def points(self) -> Tuple[Point, ...]:
        return tuple(itertools.product((0, 1, 2), repeat=self.arity))

    def expected(self, point: Point) -> bool:
        if self.out_of_grammar:
            # A parity interaction is deliberately absent from the candidate
            # grammar and tests explicit "none of my theories fit" behaviour.
            return sum(point) % 2 == 1
        assert self.truth is not None
        return self.truth.predict(point)

    def observe(self, point: Point, *, trial: int) -> bool:
        expected = self.expected(point)
        digest = hashlib.sha256(
            (
                f"phase43:{self.seed}:{trial}:"
                + ",".join(str(value) for value in point)
            ).encode("utf-8")
        ).digest()
        probability = int.from_bytes(digest[:8], "big") / float(2**64)
        return not expected if probability < NOISE else expected


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase43_compositional_program_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _candidate_programs(arity: int) -> List[Program]:
    raw: List[Program] = [
        Program("parameter", threshold)
        for threshold in range(1, 2 * arity + 1)
    ]
    raw.extend(
        Program("exception", threshold, primary=index)
        for index in range(arity)
        for threshold in range(1, 2 * arity + 1)
    )
    raw.extend(
        Program(
            "latent",
            threshold,
            primary=left,
            secondary=right,
        )
        for left in range(arity)
        for right in range(left + 1, arity)
        for threshold in range(0, 2 * max(1, arity - 2) + 1)
    )
    raw.extend(
        Program("operator", threshold, width=width)
        for width in (0, 1)
        for threshold in range(1, 2 * arity + 1)
    )
    points = tuple(itertools.product((0, 1, 2), repeat=arity))
    representatives: Dict[Tuple[bool, ...], Program] = {}
    for program in sorted(
        raw,
        key=lambda row: (
            row.complexity,
            FAMILY_ORDER.index(row.family),
            row,
        ),
    ):
        signature = tuple(program.predict(point) for point in points)
        representatives.setdefault(signature, program)
    return sorted(representatives.values())


def _family_candidates(arity: int, family: str) -> List[Program]:
    points = tuple(itertools.product((0, 1, 2), repeat=arity))
    rows = []
    for program in _candidate_programs(arity):
        if program.family != family:
            continue
        positive_rate = sum(
            int(program.predict(point)) for point in points
        ) / len(points)
        # Sealed truth programs must express a substantive distinction.  An
        # always-false or nearly constant program can be syntactically complex
        # while providing no meaningful test of exception, latent or operator
        # invention.
        if 0.05 <= positive_rate <= 0.95:
            rows.append(program)
    return rows


def _normalise(
    posterior: Mapping[Program, float],
) -> Dict[Program, float]:
    total = sum(posterior.values())
    if total <= 0.0:
        size = len(posterior)
        return {program: 1.0 / size for program in posterior}
    return {
        program: probability / total
        for program, probability in posterior.items()
    }


def _prior(candidates: Sequence[Program]) -> Dict[Program, float]:
    return _normalise(
        {
            program: math.exp(-0.35 * (program.complexity - 1))
            for program in candidates
        }
    )


def _entropy(probabilities: Iterable[float]) -> float:
    return -sum(
        probability * math.log2(probability)
        for probability in probabilities
        if probability > 0.0
    )


def _likelihood(
    program: Program,
    point: Point,
    outcome: bool,
) -> float:
    return 1.0 - NOISE if program.predict(point) == outcome else NOISE


def _update(
    posterior: Mapping[Program, float],
    point: Point,
    outcome: bool,
) -> Dict[Program, float]:
    return _normalise(
        {
            program: probability * _likelihood(program, point, outcome)
            for program, probability in posterior.items()
        }
    )


def _probe_cost(point: Point) -> float:
    return 1.0 + 0.025 * sum(point)


def _information_gain(
    posterior: Mapping[Program, float],
    point: Point,
) -> float:
    prior_entropy = _entropy(posterior.values())
    positive = sum(
        probability
        * (1.0 - NOISE if program.predict(point) else NOISE)
        for program, probability in posterior.items()
    )
    expected_entropy = 0.0
    for outcome, probability in ((True, positive), (False, 1.0 - positive)):
        if probability <= 0.0:
            continue
        expected_entropy += probability * _entropy(
            _update(posterior, point, outcome).values()
        )
    return prior_entropy - expected_entropy


def _active_point(
    posterior: Mapping[Program, float],
    available: Sequence[Tuple[Point, int]],
) -> Tuple[Point, int]:
    return max(
        available,
        key=lambda row: (
            _information_gain(posterior, row[0]) / _probe_cost(row[0]),
            _information_gain(posterior, row[0]),
            -row[1],
            row[0],
        ),
    )


def _verification_points(
    world: ProgramWorld,
    used: Sequence[Point],
    *,
    count: int = 16,
) -> List[Point]:
    used_set = set(used)
    available = [
        point for point in world.points
        if point not in used_set
    ]
    rng = random.Random(world.seed + 90_001)
    rng.shuffle(available)
    if len(available) < count:
        fallback = list(world.points)
        rng.shuffle(fallback)
        available.extend(fallback)
    return available[:count]


def _induce(
    world: ProgramWorld,
    *,
    active: bool,
    seed: int,
    max_discovery: int = 54,
) -> Dict[str, Any]:
    candidates = _candidate_programs(world.arity)
    posterior = _prior(candidates)
    available = [
        (point, repeat)
        for repeat in range(3)
        for point in world.points
    ]
    rng = random.Random(seed)
    trace: List[Dict[str, Any]] = []
    for _ in range(max_discovery):
        selected = (
            _active_point(posterior, available)
            if active else rng.choice(available)
        )
        available.remove(selected)
        point, repeat = selected
        gain = _information_gain(posterior, point)
        outcome = world.observe(
            point,
            trial=repeat * 10_000 + len(trace),
        )
        posterior = _update(posterior, point, outcome)
        champion = max(posterior, key=posterior.get)
        trace.append(
            {
                "point": list(point),
                "repeat": repeat,
                "outcome": int(outcome),
                "information_gain": gain,
                "cost": _probe_cost(point),
                "champion_id": champion.program_id,
                "champion_family": champion.family,
                "confidence": posterior[champion],
            }
        )
        if len(trace) >= 12 and posterior[champion] >= 0.985:
            break
    champion = max(posterior, key=posterior.get)
    verification = []
    for index, point in enumerate(
        _verification_points(
            world,
            [tuple(row["point"]) for row in trace],
        )
    ):
        outcome = world.observe(point, trial=800_000 + index)
        verification.append(
            {
                "point": list(point),
                "outcome": int(outcome),
                "prediction": int(champion.predict(point)),
                "agreement": champion.predict(point) == outcome,
            }
        )
    verification_accuracy = sum(
        int(row["agreement"]) for row in verification
    ) / len(verification)
    accepted = (
        posterior[champion] >= 0.985
        and verification_accuracy >= 0.875
    )
    predictive_accuracy = sum(
        int(champion.predict(point) == world.expected(point))
        for point in world.points
    ) / len(world.points)
    return {
        "status": "THEORY_ACCEPTED" if accepted else "NO_ADEQUATE_THEORY",
        "accepted": accepted,
        "champion": asdict(champion),
        "champion_id": champion.program_id,
        "revision_kind": champion.revision_kind,
        "confidence": posterior[champion],
        "discovery_trials": len(trace),
        "verification_trials": len(verification),
        "environmental_trials": len(trace) + len(verification),
        "total_cost": sum(row["cost"] for row in trace)
        + sum(_probe_cost(tuple(row["point"])) for row in verification),
        "verification_accuracy": verification_accuracy,
        "predictive_accuracy": predictive_accuracy,
        "trace": trace,
        "verification": verification,
        "posterior_top": [
            {
                "program": asdict(program),
                "program_id": program.program_id,
                "probability": probability,
            }
            for program, probability in sorted(
                posterior.items(),
                key=lambda row: row[1],
                reverse=True,
            )[:8]
        ],
    }


def _make_worlds(
    count: int,
    *,
    seed: int,
    external: bool = False,
) -> List[ProgramWorld]:
    rng = random.Random(seed)
    domains = EXTERNAL_DOMAINS if external else DOMAINS
    rows = []
    for index in range(count):
        arity = 3 + index % 3
        family = FAMILY_ORDER[index % len(FAMILY_ORDER)]
        options = _family_candidates(arity, family)
        if not options:
            raise RuntimeError(f"NO_CANONICAL_{family.upper()}_PROGRAM")
        truth = rng.choice(options)
        prefix = "external" if external else "sealed"
        rows.append(
            ProgramWorld(
                world_id=f"phase43:{prefix}:{index:03d}",
                domain=domains[index % len(domains)],
                symbols=tuple(
                    f"{prefix}_{index}_{chr(97 + offset)}"
                    for offset in range(arity)
                ),
                truth=truth,
                seed=seed + index * 29,
            )
        )
    return rows


def _make_ood_worlds(count: int, *, seed: int) -> List[ProgramWorld]:
    return [
        ProgramWorld(
            world_id=f"phase43:ood:{index:03d}",
            domain=EXTERNAL_DOMAINS[index % len(EXTERNAL_DOMAINS)],
            symbols=tuple(
                f"ood_{index}_{chr(97 + offset)}"
                for offset in range(3 + index % 3)
            ),
            truth=None,
            seed=seed + index * 31,
            out_of_grammar=True,
        )
        for index in range(count)
    ]


def _evaluate_world(
    world: ProgramWorld,
    *,
    index: int,
) -> Dict[str, Any]:
    active = _induce(
        world,
        active=True,
        seed=43_000 + index,
    )
    random_control = _induce(
        world,
        active=False,
        seed=86_000 + index,
    )
    truth = world.truth
    exact = bool(
        truth is not None
        and active["accepted"]
        and active["champion_id"] == truth.program_id
    )
    return {
        "world_id": world.world_id,
        "domain": world.domain,
        "symbols": list(world.symbols),
        "arity": world.arity,
        "out_of_grammar": world.out_of_grammar,
        "truth": asdict(truth) if truth is not None else None,
        "truth_program_id": truth.program_id if truth is not None else None,
        "required_revision": (
            truth.revision_kind if truth is not None else "ABSTAIN"
        ),
        "active": active,
        "random_control": random_control,
        "exact_program": exact,
        "family_diagnosis_correct": bool(
            truth is not None
            and active["accepted"]
            and active["revision_kind"] == truth.revision_kind
        ),
        "safe_abstention": bool(
            world.out_of_grammar and not active["accepted"]
        ),
        "complexity_excess": (
            max(
                0,
                Program(**active["champion"]).complexity
                - truth.complexity,
            )
            if truth is not None and active["accepted"]
            else 0
        ),
    }


def run_compositional_theory_program_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    sealed_worlds: int = 48,
    external_worlds: int = 16,
    ood_worlds: int = 12,
) -> Dict[str, Any]:
    state_path = state_path.resolve()
    if result_path is not None:
        result_path = result_path.resolve()
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    parent_id = "procedure_adaptive_schema_revision_d5ea7bf85c36"
    runtime.skills.promote(
        ProcedureCandidate(
            procedure_id=parent_id,
            goal="compositional_theory_program_induction",
            steps=["phase42_adaptive_schema_revision"],
            score=0.0,
            success=True,
            evidence={"evaluation": "phase42_dependency"},
        )
    )
    worlds = (
        _make_worlds(sealed_worlds, seed=430_043)
        + _make_worlds(
            external_worlds,
            seed=431_043,
            external=True,
        )
        + _make_ood_worlds(ood_worlds, seed=432_043)
    )
    rows = []
    for index, world in enumerate(worlds):
        row = _evaluate_world(world, index=index)
        runtime.store.state["compositional_theory_programs"][
            world.world_id
        ] = row
        runtime.store.state["program_induction_sessions"].append(
            {
                "world_id": world.world_id,
                "status": row["active"]["status"],
                "revision_kind": row["active"]["revision_kind"],
                "program_id": row["active"]["champion_id"],
                "verified": (
                    row["exact_program"]
                    if not world.out_of_grammar
                    else row["safe_abstention"]
                ),
            }
        )
        runtime.store.commit(reason=f"phase43_world:{world.world_id}")
        rows.append(row)
    in_grammar = [row for row in rows if not row["out_of_grammar"]]
    external = [
        row for row in in_grammar
        if row["domain"] in EXTERNAL_DOMAINS
    ]
    ood = [row for row in rows if row["out_of_grammar"]]
    family_metrics = {}
    for family in FAMILY_ORDER:
        members = [
            row for row in in_grammar
            if row["truth"]["family"] == family
        ]
        family_metrics[family] = {
            "worlds": len(members),
            "exact_program_accuracy": sum(
                int(row["exact_program"]) for row in members
            ) / len(members),
            "family_diagnosis_accuracy": sum(
                int(row["family_diagnosis_correct"]) for row in members
            ) / len(members),
            "predictive_accuracy": sum(
                row["active"]["predictive_accuracy"] for row in members
            ) / len(members),
        }
    mean_active = sum(
        row["active"]["environmental_trials"] for row in in_grammar
    ) / len(in_grammar)
    mean_random = sum(
        row["random_control"]["environmental_trials"]
        for row in in_grammar
    ) / len(in_grammar)
    gate = {
        "sealed_in_grammar_worlds": len(in_grammar),
        "out_of_grammar_worlds": len(ood),
        "exact_program_accuracy": sum(
            int(row["exact_program"]) for row in in_grammar
        ) / len(in_grammar),
        "weakest_family_accuracy": min(
            metrics["exact_program_accuracy"]
            for metrics in family_metrics.values()
        ),
        "revision_kind_accuracy": sum(
            int(row["family_diagnosis_correct"]) for row in in_grammar
        ) / len(in_grammar),
        "predictive_accuracy": sum(
            row["active"]["predictive_accuracy"] for row in in_grammar
        ) / len(in_grammar),
        "external_family_accuracy": sum(
            int(row["exact_program"]) for row in external
        ) / len(external),
        "safe_ood_abstention": sum(
            int(row["safe_abstention"]) for row in ood
        ) / len(ood),
        "unsafe_forced_theories": sum(
            int(not row["safe_abstention"]) for row in ood
        ),
        "mean_active_environmental_trials": mean_active,
        "mean_random_environmental_trials": mean_random,
        "active_trial_reduction": (
            1.0 - mean_active / mean_random if mean_random else 0.0
        ),
        "complexity_violations": sum(
            int(row["complexity_excess"] > 0) for row in in_grammar
        ),
        "provenance_complete": sum(
            int(
                bool(row["active"]["trace"])
                and bool(row["active"]["verification"])
                and bool(row["active"]["champion_id"])
            )
            for row in rows
        ) / len(rows),
    }
    errors = []
    requirements = (
        ("exact_program_accuracy", 0.90),
        ("weakest_family_accuracy", 0.85),
        ("revision_kind_accuracy", 0.95),
        ("predictive_accuracy", 0.98),
        ("external_family_accuracy", 0.90),
        ("safe_ood_abstention", 0.90),
        ("active_trial_reduction", 0.10),
        ("provenance_complete", 1.0),
    )
    for name, minimum in requirements:
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum:.2f}")
    if gate["unsafe_forced_theories"]:
        errors.append("UNSAFE_OUT_OF_GRAMMAR_THEORY_FORCED")
    if gate["complexity_violations"]:
        errors.append("UNJUSTIFIED_COMPLEXITY")
    gate["accepted"] = not errors
    gate["errors"] = errors
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_compositional_theory_program_"
            + _canonical_hash(
                {
                    "parent": parent_id,
                    "gate": gate,
                    "families": family_metrics,
                }
            )[:12]
        ),
        goal="compositional_theory_program_induction",
        steps=[
            "represent_multi_valued_intervention_state",
            "maintain_competing_compositional_programs",
            "diagnose_parameter_exception_latent_or_operator_revision",
            "select_experiments_by_information_gain_per_cost",
            "verify_program_on_unseen_interventions",
            "abstain_when_no_program_class_fits",
            "persist_program_evidence_and_revision_provenance",
        ],
        score=gate["exact_program_accuracy"] + gate["predictive_accuracy"],
        success=gate["accepted"],
        evidence={"evaluation": "phase43_sealed", "gate": gate},
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="phase43_compositional_theory_program")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "programs_retained": len(
            restarted.store.state["compositional_theory_programs"]
        ) == len(rows),
        "sessions_retained": len(
            restarted.store.state["program_induction_sessions"]
        ) == len(rows),
        "champion_retained": (
            restarted.store.state["champions"].get(
                "compositional_theory_program_induction"
            ) == candidate.procedure_id
        ),
        "relearning_worlds": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and all(
            (
                restart["programs_retained"],
                restart["sessions_retained"],
                restart["champion_retained"],
            )
        )
    )
    result = {
        "schema_version": "aion.hexcore.compositional_program.v1",
        "benchmark": "compositional_probabilistic_program_induction",
        "passed": passed,
        "gate": gate,
        "family_metrics": family_metrics,
        "sealed": {
            "rows": rows,
            "in_grammar_worlds": len(in_grammar),
            "external_worlds": len(external),
            "ood_worlds": len(ood),
        },
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "gold_isolation": {
            "solver_receives_truth_program": False,
            "solver_receives_revision_kind": False,
            "solver_receives_ood_label": False,
            "gold_used_only_by_evaluator": True,
        },
        "boundary_statement": (
            "Phase 43 induces bounded compositional programs over ternary "
            "variables, including parameter thresholds, contextual vetoes, "
            "pair-derived latent predicates and a range operator. The grammar, "
            "simulator, variables, noise model and verification oracle remain "
            "engineered. This is not unrestricted program synthesis, arbitrary "
            "scientific law discovery, real-world causal identification or AGI."
        ),
        "created_at": _utc_timestamp(),
    }
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run HexCore Phase 43 compositional theory induction."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--sealed-worlds", type=int, default=48)
    parser.add_argument("--external-worlds", type=int, default=16)
    parser.add_argument("--ood-worlds", type=int, default=12)
    args = parser.parse_args()
    result = run_compositional_theory_program_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        sealed_worlds=args.sealed_worlds,
        external_worlds=args.external_worlds,
        ood_worlds=args.ood_worlds,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
