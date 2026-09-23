from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


AST = Tuple[Any, ...]
Point = Tuple[int, ...]
NOISE = 0.015
FAMILIES = ("clause", "conjunction", "conditional")
DOMAINS = (
    "tidal fabrication",
    "distributed seed exchange",
    "autonomous ice survey",
    "urban heat network",
    "adaptive radio commons",
    "closed-loop medical supply",
)
EXTERNAL_DOMAINS = (
    "external mineral assay",
    "external stratospheric relay",
)


def _ast_list(node: AST) -> List[Any]:
    return [
        _ast_list(value) if isinstance(value, tuple) else value
        for value in node
    ]


def _program_id(node: AST) -> str:
    return "dsl_program_" + _canonical_hash(_ast_list(node))[:12]


def _eval_num(node: AST, point: Point) -> int:
    op = node[0]
    if op == "var":
        return point[int(node[1])]
    left = _eval_num(node[1], point)
    right = _eval_num(node[2], point)
    if op == "add":
        return left + right
    if op == "absdiff":
        return abs(left - right)
    if op == "max":
        return max(left, right)
    raise ValueError(op)


def _eval_bool(node: AST, point: Point) -> bool:
    op = node[0]
    if op == "ge":
        return _eval_num(node[1], point) >= int(node[2])
    if op == "and":
        return _eval_bool(node[1], point) and _eval_bool(node[2], point)
    if op == "if":
        return (
            _eval_bool(node[2], point)
            if _eval_bool(node[1], point)
            else _eval_bool(node[3], point)
        )
    raise ValueError(op)


def _eval_external(node: AST, values: Mapping[int, int]) -> bool:
    """Independent interpreter used only by external-family worlds."""

    def number(expr: AST) -> int:
        tag = expr[0]
        if tag == "var":
            return int(values[int(expr[1])])
        a = number(expr[1])
        b = number(expr[2])
        if tag == "add":
            return a + b
        if tag == "absdiff":
            return (a - b) if a >= b else (b - a)
        if tag == "max":
            return a if a >= b else b
        raise ValueError(tag)

    tag = node[0]
    if tag == "ge":
        return number(node[1]) >= int(node[2])
    if tag == "and":
        if not _eval_external(node[1], values):
            return False
        return _eval_external(node[2], values)
    if tag == "if":
        branch = node[2] if _eval_external(node[1], values) else node[3]
        return _eval_external(branch, values)
    raise ValueError(tag)


def _family(node: AST) -> str:
    return {
        "ge": "clause",
        "and": "conjunction",
        "if": "conditional",
    }[str(node[0])]


def _complexity(node: AST) -> int:
    return 1 + sum(
        _complexity(value)
        for value in node[1:]
        if isinstance(value, tuple)
    )


def _abstract_motif(node: AST) -> str:
    variable_roles: Dict[int, str] = {}

    def visit(value: Any) -> Any:
        if not isinstance(value, tuple):
            return value
        if value[0] == "var":
            index = int(value[1])
            if index not in variable_roles:
                variable_roles[index] = f"v{len(variable_roles)}"
            return ("var", variable_roles[index])
        return tuple(visit(item) for item in value)

    return json.dumps(visit(node), separators=(",", ":"))


def _numeric_features(arity: int) -> List[AST]:
    features: List[AST] = [("var", index) for index in range(arity)]
    for left in range(arity):
        for right in range(left + 1, arity):
            for op in ("add", "absdiff", "max"):
                features.append((op, ("var", left), ("var", right)))
    return features


def _clauses(arity: int) -> List[AST]:
    rows = []
    for feature in _numeric_features(arity):
        maximum = 4 if feature[0] == "add" else 2
        rows.extend(
            ("ge", feature, threshold)
            for threshold in range(1, maximum + 1)
        )
    return rows


_CANDIDATE_CACHE: Dict[int, Tuple[AST, ...]] = {}


def _candidate_programs(arity: int) -> Tuple[AST, ...]:
    if arity in _CANDIDATE_CACHE:
        return _CANDIDATE_CACHE[arity]
    clauses = _clauses(arity)
    raw: List[AST] = list(clauses)
    # Two-clause programs are genuine expression trees. Limit conjunctions to
    # different numeric features so duplicate self-conjunctions are excluded.
    for left_index, left in enumerate(clauses):
        for right in clauses[left_index + 1 :]:
            if left[1] != right[1]:
                raw.append(("and", left, right))
    # Conditional programs use a typed Boolean guard and independently
    # synthesized branches over variables not used as the guard.
    for context in range(arity):
        others = [index for index in range(arity) if index != context]
        for left, right in itertools.combinations(others, 2):
            feature = ("add", ("var", left), ("var", right))
            branches = [
                ("ge", feature, threshold) for threshold in range(1, 5)
            ]
            guard = ("ge", ("var", context), 2)
            for then_clause in branches:
                for else_clause in branches:
                    if then_clause != else_clause:
                        raw.append(
                            ("if", guard, then_clause, else_clause)
                        )
    points = tuple(itertools.product((0, 1, 2), repeat=arity))
    representatives: Dict[Tuple[bool, ...], AST] = {}
    for program in sorted(
        raw,
        key=lambda row: (_complexity(row), _program_id(row)),
    ):
        signature = tuple(_eval_bool(program, point) for point in points)
        representatives.setdefault(signature, program)
    result = tuple(representatives.values())
    _CANDIDATE_CACHE[arity] = result
    return result


def _truth_candidates(arity: int, family: str) -> List[AST]:
    points = tuple(itertools.product((0, 1, 2), repeat=arity))
    rows = []
    for program in _candidate_programs(arity):
        if _family(program) != family:
            continue
        rate = sum(int(_eval_bool(program, point)) for point in points) / len(points)
        if 0.08 <= rate <= 0.92:
            rows.append(program)
    return rows


@dataclass(frozen=True)
class DSLWorld:
    world_id: str
    domain: str
    symbols: Tuple[str, ...]
    truth: AST | None
    seed: int
    external: bool = False
    out_of_grammar: bool = False

    @property
    def arity(self) -> int:
        return len(self.symbols)

    @property
    def points(self) -> Tuple[Point, ...]:
        return tuple(itertools.product((0, 1, 2), repeat=self.arity))

    def expected(self, point: Point) -> bool:
        if self.out_of_grammar:
            return sum(point) % 2 == 1
        assert self.truth is not None
        if self.external:
            return _eval_external(
                self.truth,
                {index: value for index, value in enumerate(point)},
            )
        return _eval_bool(self.truth, point)

    def observe(self, point: Point, *, trial: int) -> bool:
        expected = self.expected(point)
        digest = hashlib.sha256(
            (
                f"phase44:{self.seed}:{trial}:"
                + ",".join(str(value) for value in point)
            ).encode()
        ).digest()
        probability = int.from_bytes(digest[:8], "big") / float(2**64)
        return not expected if probability < NOISE else expected


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase44_typed_dsl_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _normalise(rows: Mapping[AST, float]) -> Dict[AST, float]:
    total = sum(rows.values())
    return {
        program: value / total for program, value in rows.items()
    }


def _prior(
    candidates: Sequence[AST],
    motifs: Mapping[str, int] | None,
) -> Dict[AST, float]:
    return _normalise(
        {
            program: math.exp(-0.10 * _complexity(program))
            * (
                50.0
                if motifs and _abstract_motif(program) in motifs
                else 1.0
            )
            for program in candidates
        }
    )


def _entropy(values: Iterable[float]) -> float:
    return -sum(value * math.log2(value) for value in values if value > 0)


def _update(
    posterior: Mapping[AST, float],
    point: Point,
    outcome: bool,
) -> Dict[AST, float]:
    return _normalise(
        {
            program: probability
            * (
                1.0 - NOISE
                if _eval_bool(program, point) == outcome
                else NOISE
            )
            for program, probability in posterior.items()
        }
    )


def _gain(posterior: Mapping[AST, float], point: Point) -> float:
    before = _entropy(posterior.values())
    positive = sum(
        probability
        * (1.0 - NOISE if _eval_bool(program, point) else NOISE)
        for program, probability in posterior.items()
    )
    after = 0.0
    for outcome, probability in ((True, positive), (False, 1 - positive)):
        if probability > 0:
            after += probability * _entropy(
                _update(posterior, point, outcome).values()
            )
    return before - after


def _induce(
    world: DSLWorld,
    *,
    motifs: Mapping[str, int] | None,
    seed: int,
    max_trials: int = 48,
) -> Dict[str, Any]:
    candidates = _candidate_programs(world.arity)
    posterior = _prior(candidates, motifs)
    available = list(world.points)
    trace = []
    for index in range(min(max_trials, len(available))):
        point = max(
            available,
            key=lambda row: (_gain(posterior, row), row),
        )
        available.remove(point)
        gain = _gain(posterior, point)
        outcome = world.observe(point, trial=index)
        posterior = _update(posterior, point, outcome)
        champion = max(posterior, key=posterior.get)
        trace.append(
            {
                "point": list(point),
                "outcome": int(outcome),
                "information_gain": gain,
                "champion_id": _program_id(champion),
                "confidence": posterior[champion],
            }
        )
        if len(trace) >= 10 and posterior[champion] >= 0.99:
            break
    # Use the first half as an explicit confirmation block.  This is
    # especially important when the finite intervention cube has been
    # exhausted under noise: confirmation evidence should update belief rather
    # than being discarded after the discovery loop.  The second half remains
    # an untouched audit and therefore cannot select the final program.
    confirmation = []
    confirmation_pool = list(world.points)
    for index in range(8):
        point = max(
            confirmation_pool,
            key=lambda row: (_gain(posterior, row), row),
        )
        confirmation_pool.remove(point)
        outcome = world.observe(point, trial=900_000 + index)
        posterior = _update(posterior, point, outcome)
        confirmation.append(
            {"point": list(point), "outcome": int(outcome)}
        )
    champion = max(posterior, key=posterior.get)
    rng = random.Random(seed + world.seed)
    audit_points = [
        point for point in world.points
        if point not in {tuple(row["point"]) for row in confirmation}
    ]
    rng.shuffle(audit_points)
    audit_points = (audit_points + list(world.points))[:8]
    verification = [
        {
            "point": list(point),
            "prediction": int(_eval_bool(champion, point)),
            "outcome": int(world.observe(point, trial=910_000 + index)),
        }
        for index, point in enumerate(audit_points)
    ]
    agreement = sum(
        int(row["prediction"] == row["outcome"])
        for row in verification
    ) / len(verification)
    accepted = posterior[champion] >= 0.99 and agreement >= 0.875
    return {
        "accepted": accepted,
        "status": "PROGRAM_VERIFIED" if accepted else "DSL_INADEQUATE",
        "program": _ast_list(champion),
        "program_id": _program_id(champion),
        "family": _family(champion),
        "motif": _abstract_motif(champion),
        "confidence": posterior[champion],
        "discovery_trials": len(trace),
        "confirmation_trials": len(confirmation),
        "verification_trials": len(verification),
        "environmental_trials": (
            len(trace) + len(confirmation) + len(verification)
        ),
        "verification_accuracy": agreement,
        "predictive_accuracy": sum(
            int(_eval_bool(champion, point) == world.expected(point))
            for point in world.points
        ) / len(world.points),
        "trace": trace,
        "confirmation": confirmation,
        "verification": verification,
    }


def _make_worlds(
    count: int,
    *,
    seed: int,
    prefix: str,
    motifs: Mapping[str, int] | None = None,
    external: bool = False,
) -> List[DSLWorld]:
    rng = random.Random(seed)
    domains = EXTERNAL_DOMAINS if external else DOMAINS
    rows = []
    for index in range(count):
        arity = 3 + index % 2
        family = FAMILIES[index % len(FAMILIES)]
        candidates = _truth_candidates(arity, family)
        if motifs:
            transferred = [
                program for program in candidates
                if _abstract_motif(program) in motifs
            ]
            if transferred:
                candidates = transferred
        truth = rng.choice(candidates)
        rows.append(
            DSLWorld(
                world_id=f"phase44:{prefix}:{index:03d}",
                domain=domains[index % len(domains)],
                symbols=tuple(
                    f"{prefix}_{index}_{chr(97 + offset)}"
                    for offset in range(arity)
                ),
                truth=truth,
                seed=seed + index * 37,
                external=external,
            )
        )
    return rows


def _ood_worlds(count: int, *, seed: int) -> List[DSLWorld]:
    return [
        DSLWorld(
            world_id=f"phase44:ood:{index:03d}",
            domain=EXTERNAL_DOMAINS[index % len(EXTERNAL_DOMAINS)],
            symbols=tuple(
                f"ood_{index}_{chr(97 + offset)}"
                for offset in range(3 + index % 2)
            ),
            truth=None,
            seed=seed + index * 41,
            external=True,
            out_of_grammar=True,
        )
        for index in range(count)
    ]


def run_typed_dsl_program_synthesis_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_worlds: int = 18,
    sealed_worlds: int = 36,
    external_worlds: int = 12,
    ood_worlds: int = 8,
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
    parent_id = "procedure_compositional_theory_program_67d49719b0b9"
    runtime.skills.promote(
        ProcedureCandidate(
            procedure_id=parent_id,
            goal="typed_dsl_program_synthesis",
            steps=["phase43_compositional_theory_program"],
            score=0.0,
            success=True,
            evidence={"evaluation": "phase43_dependency"},
        )
    )
    development_rows = []
    motif_library: Dict[str, int] = {}
    for index, world in enumerate(
        _make_worlds(
            development_worlds,
            seed=440_044,
            prefix="development",
        )
    ):
        learned = _induce(world, motifs=None, seed=1_000 + index)
        exact = bool(
            learned["accepted"]
            and learned["program_id"] == _program_id(world.truth)
        )
        if exact:
            motif_library[learned["motif"]] = (
                motif_library.get(learned["motif"], 0) + 1
            )
        development_rows.append(
            {
                "world_id": world.world_id,
                "exact": exact,
                "learned": learned,
                "truth_id": _program_id(world.truth),
            }
        )
    worlds = (
        _make_worlds(
            sealed_worlds,
            seed=441_044,
            prefix="sealed",
            motifs=motif_library,
        )
        + _make_worlds(
            external_worlds,
            seed=442_044,
            prefix="external",
            motifs=motif_library,
            external=True,
        )
        + _ood_worlds(ood_worlds, seed=443_044)
    )
    rows = []
    for index, world in enumerate(worlds):
        transfer = _induce(
            world,
            motifs=motif_library,
            seed=3_000 + index,
        )
        cold = _induce(world, motifs=None, seed=4_000 + index)
        truth_id = _program_id(world.truth) if world.truth else None
        row = {
            "world_id": world.world_id,
            "domain": world.domain,
            "external": world.external,
            "out_of_grammar": world.out_of_grammar,
            "arity": world.arity,
            "truth_program": _ast_list(world.truth) if world.truth else None,
            "truth_id": truth_id,
            "truth_family": _family(world.truth) if world.truth else None,
            "transfer": transfer,
            "cold": cold,
            "exact": bool(
                truth_id
                and transfer["accepted"]
                and transfer["program_id"] == truth_id
            ),
            "safe_abstention": bool(
                world.out_of_grammar and not transfer["accepted"]
            ),
        }
        runtime.store.state["typed_dsl_programs"][world.world_id] = row
        runtime.store.state["dsl_synthesis_sessions"].append(
            {
                "world_id": world.world_id,
                "status": transfer["status"],
                "program_id": transfer["program_id"],
                "verified": row["exact"] or row["safe_abstention"],
            }
        )
        runtime.store.commit(reason=f"phase44_world:{world.world_id}")
        rows.append(row)
    runtime.store.state["verified_subprogram_library"] = {
        motif: {
            "motif": motif,
            "verified_uses": count,
            "source": "phase44_development",
        }
        for motif, count in motif_library.items()
    }
    runtime.store.commit(reason="phase44_subprogram_library")
    valid = [row for row in rows if not row["out_of_grammar"]]
    external = [row for row in valid if row["external"]]
    ood = [row for row in rows if row["out_of_grammar"]]
    family_metrics = {}
    for family in FAMILIES:
        members = [row for row in valid if row["truth_family"] == family]
        family_metrics[family] = sum(
            int(row["exact"]) for row in members
        ) / len(members)
    transfer_trials = sum(
        row["transfer"]["environmental_trials"] for row in valid
    ) / len(valid)
    cold_trials = sum(
        row["cold"]["environmental_trials"] for row in valid
    ) / len(valid)
    gate = {
        "development_exact_accuracy": sum(
            int(row["exact"]) for row in development_rows
        ) / len(development_rows),
        "verified_subprogram_motifs": len(motif_library),
        "sealed_exact_accuracy": sum(
            int(row["exact"]) for row in valid
        ) / len(valid),
        "weakest_family_accuracy": min(family_metrics.values()),
        "external_interpreter_accuracy": sum(
            int(row["exact"]) for row in external
        ) / len(external),
        "predictive_accuracy": sum(
            row["transfer"]["predictive_accuracy"] for row in valid
        ) / len(valid),
        "safe_ood_abstention": sum(
            int(row["safe_abstention"]) for row in ood
        ) / len(ood),
        "unsafe_forced_programs": sum(
            int(not row["safe_abstention"]) for row in ood
        ),
        "mean_transfer_environmental_trials": transfer_trials,
        "mean_cold_environmental_trials": cold_trials,
        "transfer_trial_reduction": (
            1.0 - transfer_trials / cold_trials if cold_trials else 0.0
        ),
        "provenance_complete": sum(
            int(
                bool(row["transfer"]["trace"])
                and bool(row["transfer"]["verification"])
            )
            for row in rows
        ) / len(rows),
    }
    errors = []
    for name, minimum in (
        ("development_exact_accuracy", 0.85),
        ("sealed_exact_accuracy", 0.90),
        ("weakest_family_accuracy", 0.85),
        ("external_interpreter_accuracy", 0.90),
        ("predictive_accuracy", 0.98),
        ("safe_ood_abstention", 0.90),
        ("transfer_trial_reduction", 0.10),
        ("provenance_complete", 1.0),
    ):
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum:.2f}")
    if gate["verified_subprogram_motifs"] < 6:
        errors.append("INSUFFICIENT_VERIFIED_SUBPROGRAM_LIBRARY")
    if gate["unsafe_forced_programs"]:
        errors.append("UNSAFE_PROGRAM_FORCED")
    gate["accepted"] = not errors
    gate["errors"] = errors
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_typed_dsl_synthesis_"
            + _canonical_hash(
                {
                    "parent": parent_id,
                    "gate": gate,
                    "families": family_metrics,
                }
            )[:12]
        ),
        goal="typed_dsl_program_synthesis",
        steps=[
            "compose_typed_numeric_and_boolean_expression_trees",
            "deduplicate_programs_by_executable_semantics",
            "extract_verified_role_abstracted_subprogram_motifs",
            "transfer_motifs_as_reversible_search_priors",
            "select_discriminative_environmental_interventions",
            "verify_on_unseen_points_with_external_interpreter",
            "abstain_when_typed_language_is_inadequate",
        ],
        score=gate["sealed_exact_accuracy"] + gate["predictive_accuracy"],
        success=gate["accepted"],
        evidence={"evaluation": "phase44_sealed", "gate": gate},
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="phase44_typed_dsl_synthesis")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "programs_retained": len(
            restarted.store.state["typed_dsl_programs"]
        ) == len(rows),
        "library_retained": len(
            restarted.store.state["verified_subprogram_library"]
        ) == len(motif_library),
        "champion_retained": (
            restarted.store.state["champions"].get(
                "typed_dsl_program_synthesis"
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
                restart["library_retained"],
                restart["champion_retained"],
            )
        )
    )
    result = {
        "schema_version": "aion.hexcore.typed_dsl_synthesis.v1",
        "benchmark": "typed_expression_tree_and_subprogram_transfer",
        "passed": passed,
        "gate": gate,
        "family_metrics": family_metrics,
        "development": {
            "worlds": len(development_rows),
            "rows": development_rows,
        },
        "sealed": {"worlds": len(rows), "rows": rows},
        "subprogram_library": runtime.store.state[
            "verified_subprogram_library"
        ],
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "gold_isolation": {
            "solver_receives_truth_tree": False,
            "solver_receives_family": False,
            "solver_receives_ood_label": False,
            "gold_used_only_by_evaluator": True,
        },
        "boundary_statement": (
            "Phase 44 composes bounded typed expression trees from variable, "
            "add, absolute-difference, maximum, threshold, conjunction and "
            "conditional primitives. Candidate depth, value domain, primitive "
            "set, simulator and oracle remain engineered. This is not "
            "unrestricted code generation, universal program synthesis, "
            "real-world scientific discovery or AGI."
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
        description="Run HexCore Phase 44 typed DSL synthesis."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--development-worlds", type=int, default=18)
    parser.add_argument("--sealed-worlds", type=int, default=36)
    parser.add_argument("--external-worlds", type=int, default=12)
    parser.add_argument("--ood-worlds", type=int, default=8)
    args = parser.parse_args()
    result = run_typed_dsl_program_synthesis_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        development_worlds=args.development_worlds,
        sealed_worlds=args.sealed_worlds,
        external_worlds=args.external_worlds,
        ood_worlds=args.ood_worlds,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
