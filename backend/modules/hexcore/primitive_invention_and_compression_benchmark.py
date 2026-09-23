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
from backend.modules.hexcore.typed_dsl_program_synthesis_benchmark import (
    _candidate_programs as phase44_candidates,
    _eval_bool as phase44_eval,
)


Point = Tuple[int, ...]
NOISE = 0.0125
PAIR_CELLS = ((0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (2, 2))
DOMAINS = (
    "adaptive ceramics",
    "distributed wetland control",
    "orbital materials exchange",
    "autonomous crop microbiome",
    "cooperative thermal grid",
    "deep-ocean instrument mesh",
)
EXTERNAL_DOMAINS = (
    "external photonic assay",
    "external alpine logistics",
)


def _cell_index(left: int, right: int) -> int:
    pair = (left, right) if left <= right else (right, left)
    return PAIR_CELLS.index(pair)


def _table_value(mask: int, left: int, right: int) -> bool:
    return bool(mask & (1 << _cell_index(left, right)))


def _table_bits(mask: int) -> Tuple[int, ...]:
    return tuple(int(bool(mask & (1 << index))) for index in range(6))


@dataclass(frozen=True, order=True)
class PrimitiveProgram:
    primitive_mask: int
    left: int
    right: int
    context: int = -1
    context_threshold: int = 1

    def predict(self, point: Point) -> bool:
        relation = _table_value(
            self.primitive_mask,
            point[self.left],
            point[self.right],
        )
        if self.context < 0:
            return relation
        return relation and point[self.context] >= self.context_threshold

    @property
    def primitive_id(self) -> str:
        return "invented_predicate_" + _canonical_hash(
            {"symmetric_table": _table_bits(self.primitive_mask)}
        )[:12]

    @property
    def program_id(self) -> str:
        return "primitive_program_" + _canonical_hash(asdict(self))[:12]

    @property
    def complexity(self) -> int:
        return 2 + int(self.context >= 0)


_PROGRAM_CACHE: Dict[int, Tuple[PrimitiveProgram, ...]] = {}
_ELIGIBLE_CACHE: Dict[int, Tuple[PrimitiveProgram, ...]] = {}


def _programs(arity: int) -> Tuple[PrimitiveProgram, ...]:
    if arity in _PROGRAM_CACHE:
        return _PROGRAM_CACHE[arity]
    raw = []
    for mask in range(1, 63):
        positive_cells = sum(_table_bits(mask))
        if positive_cells not in {2, 3, 4}:
            continue
        for left, right in itertools.combinations(range(arity), 2):
            raw.append(PrimitiveProgram(mask, left, right))
            for context in range(arity):
                if context in {left, right}:
                    continue
                for threshold in (1, 2):
                    raw.append(
                        PrimitiveProgram(
                            mask,
                            left,
                            right,
                            context,
                            threshold,
                        )
                    )
    points = tuple(itertools.product((0, 1, 2), repeat=arity))
    representatives: Dict[Tuple[bool, ...], PrimitiveProgram] = {}
    for program in sorted(
        raw,
        key=lambda row: (row.complexity, row),
    ):
        signature = tuple(program.predict(point) for point in points)
        representatives.setdefault(signature, program)
    result = tuple(representatives.values())
    _PROGRAM_CACHE[arity] = result
    return result


def _base_dsl_can_express(program: PrimitiveProgram, arity: int) -> bool:
    points = tuple(itertools.product((0, 1, 2), repeat=arity))
    signature = tuple(program.predict(point) for point in points)
    return any(
        tuple(phase44_eval(candidate, point) for point in points) == signature
        for candidate in phase44_candidates(arity)
    )


def _eligible_truths(
    arity: int,
    *,
    masks: Sequence[int] | None = None,
) -> List[PrimitiveProgram]:
    if arity not in _ELIGIBLE_CACHE:
        _ELIGIBLE_CACHE[arity] = tuple(
            program
            for program in _programs(arity)
            if not _base_dsl_can_express(program, arity)
        )
    allowed = set(masks) if masks is not None else None
    return [
        program
        for program in _ELIGIBLE_CACHE[arity]
        if allowed is None or program.primitive_mask in allowed
    ]


@dataclass(frozen=True)
class PrimitiveWorld:
    world_id: str
    domain: str
    symbols: Tuple[str, ...]
    truth: PrimitiveProgram | None
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
            # Directed relation: deliberately impossible for the symmetric
            # primitive invention grammar.
            return point[0] < point[1]
        assert self.truth is not None
        if not self.external:
            return self.truth.predict(point)
        # Independent external execution path.
        left = point[self.truth.left]
        right = point[self.truth.right]
        pair = (right, left) if right < left else (left, right)
        relation = bool(
            self.truth.primitive_mask
            & (1 << PAIR_CELLS.index(pair))
        )
        if self.truth.context >= 0:
            relation = relation and (
                point[self.truth.context]
                >= self.truth.context_threshold
            )
        return relation

    def observe(self, point: Point, *, trial: int) -> bool:
        expected = self.expected(point)
        digest = hashlib.sha256(
            (
                f"phase45:{self.seed}:{trial}:"
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
        "source": "phase45_primitive_invention_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _normalise(values: Mapping[PrimitiveProgram, float]) -> Dict[PrimitiveProgram, float]:
    total = sum(values.values())
    return {program: value / total for program, value in values.items()}


def _prior(
    candidates: Sequence[PrimitiveProgram],
    library_masks: Sequence[int] | None,
) -> Dict[PrimitiveProgram, float]:
    known = set(library_masks or ())
    return _normalise(
        {
            program: (
                35.0 if program.primitive_mask in known else 1.0
            ) * math.exp(-0.18 * program.complexity)
            for program in candidates
        }
    )


def _entropy(values: Iterable[float]) -> float:
    return -sum(value * math.log2(value) for value in values if value > 0)


def _update(
    posterior: Mapping[PrimitiveProgram, float],
    point: Point,
    outcome: bool,
) -> Dict[PrimitiveProgram, float]:
    return _normalise(
        {
            program: probability
            * (
                1.0 - NOISE
                if program.predict(point) == outcome
                else NOISE
            )
            for program, probability in posterior.items()
        }
    )


def _gain(
    posterior: Mapping[PrimitiveProgram, float],
    point: Point,
) -> float:
    before = _entropy(posterior.values())
    positive = sum(
        probability
        * (1.0 - NOISE if program.predict(point) else NOISE)
        for program, probability in posterior.items()
    )
    after = 0.0
    for outcome, probability in ((True, positive), (False, 1 - positive)):
        if probability > 0:
            after += probability * _entropy(
                _update(posterior, point, outcome).values()
            )
    return before - after


def _replay_neutral(
    candidates: Sequence[PrimitiveProgram],
    trace: Sequence[Mapping[str, Any]],
) -> Dict[PrimitiveProgram, float]:
    posterior = _prior(candidates, None)
    for row in trace:
        posterior = _update(
            posterior,
            tuple(row["point"]),
            bool(row["outcome"]),
        )
    return posterior


def _induce(
    world: PrimitiveWorld,
    *,
    library_masks: Sequence[int] | None,
    seed: int,
    max_trials: int = 45,
) -> Dict[str, Any]:
    candidates = _programs(world.arity)
    posterior = _prior(candidates, library_masks)
    available = list(world.points)
    trace = []
    fallback_at = None
    known = set(library_masks or ())
    for index in range(min(max_trials, len(available))):
        point = max(available, key=lambda row: (_gain(posterior, row), row))
        available.remove(point)
        outcome = world.observe(point, trial=index)
        posterior = _update(posterior, point, outcome)
        trace.append({"point": list(point), "outcome": int(outcome)})
        if known and fallback_at is None and len(trace) >= 6:
            known_mass = sum(
                probability
                for program, probability in posterior.items()
                if program.primitive_mask in known
            )
            if known_mass < 0.05:
                posterior = _replay_neutral(candidates, trace)
                fallback_at = len(trace)
        champion = max(posterior, key=posterior.get)
        if len(trace) >= 9 and posterior[champion] >= 0.992:
            break
    confirmation = []
    pool = list(world.points)
    pre_confirmation_champion = max(posterior, key=posterior.get)
    confirmation_budget = (
        4
        if known
        and fallback_at is None
        and pre_confirmation_champion.primitive_mask in known
        else 7
    )
    for index in range(confirmation_budget):
        point = max(pool, key=lambda row: (_gain(posterior, row), row))
        pool.remove(point)
        outcome = world.observe(point, trial=800_000 + index)
        posterior = _update(posterior, point, outcome)
        confirmation.append({"point": list(point), "outcome": int(outcome)})
    interim_champion = max(posterior, key=posterior.get)
    if (
        known
        and fallback_at is None
        and interim_champion.primitive_mask not in known
    ):
        posterior = _replay_neutral(
            candidates,
            [*trace, *confirmation],
        )
        fallback_at = len(trace) + len(confirmation)
        for index in range(len(confirmation), 7):
            point = max(pool, key=lambda row: (_gain(posterior, row), row))
            pool.remove(point)
            outcome = world.observe(point, trial=800_000 + index)
            posterior = _update(posterior, point, outcome)
            confirmation.append(
                {"point": list(point), "outcome": int(outcome)}
            )
    champion = max(posterior, key=posterior.get)
    rng = random.Random(seed + world.seed)
    audit_points = list(world.points)
    rng.shuffle(audit_points)
    audit = [
        {
            "point": list(point),
            "prediction": int(champion.predict(point)),
            "outcome": int(world.observe(point, trial=900_000 + index)),
        }
        for index, point in enumerate(audit_points[:10])
    ]
    agreement = sum(
        int(row["prediction"] == row["outcome"]) for row in audit
    ) / len(audit)
    accepted = posterior[champion] >= 0.992 and agreement >= 0.90
    return {
        "accepted": accepted,
        "status": "PRIMITIVE_PROGRAM_VERIFIED" if accepted else "INVENTION_GRAMMAR_INADEQUATE",
        "program": asdict(champion),
        "program_id": champion.program_id,
        "primitive_id": champion.primitive_id,
        "primitive_bits": list(_table_bits(champion.primitive_mask)),
        "confidence": posterior[champion],
        "surprise_fallback_at": fallback_at,
        "discovery_trials": len(trace),
        "confirmation_trials": len(confirmation),
        "audit_trials": len(audit),
        "environmental_trials": len(trace) + len(confirmation) + len(audit),
        "audit_accuracy": agreement,
        "predictive_accuracy": sum(
            int(champion.predict(point) == world.expected(point))
            for point in world.points
        ) / len(world.points),
        "trace": trace,
        "confirmation": confirmation,
        "audit": audit,
    }


def _select_masks(count: int) -> List[int]:
    # Deterministic, unnamed, non-degenerate symmetric predicates that the
    # Phase 44 DSL cannot express in at least one program context.
    candidates = []
    eligible_masks = {
        program.primitive_mask for program in _eligible_truths(3)
    }
    for mask in range(1, 63):
        if sum(_table_bits(mask)) not in {2, 3, 4}:
            continue
        if mask in eligible_masks:
            candidates.append(mask)
    return candidates[:count]


def _worlds(
    count: int,
    *,
    seed: int,
    prefix: str,
    masks: Sequence[int],
    external: bool = False,
) -> List[PrimitiveWorld]:
    rng = random.Random(seed)
    domains = EXTERNAL_DOMAINS if external else DOMAINS
    rows = []
    for index in range(count):
        arity = 3 + index % 2
        mask = masks[index % len(masks)]
        options = _eligible_truths(arity, masks=[mask])
        truth = rng.choice(options)
        rows.append(
            PrimitiveWorld(
                world_id=f"phase45:{prefix}:{index:03d}",
                domain=domains[index % len(domains)],
                symbols=tuple(
                    f"{prefix}_{index}_{chr(97 + offset)}"
                    for offset in range(arity)
                ),
                truth=truth,
                seed=seed + index * 43,
                external=external,
            )
        )
    return rows


def _ood_worlds(count: int, *, seed: int) -> List[PrimitiveWorld]:
    return [
        PrimitiveWorld(
            world_id=f"phase45:ood:{index:03d}",
            domain=EXTERNAL_DOMAINS[index % len(EXTERNAL_DOMAINS)],
            symbols=tuple(
                f"directed_{index}_{chr(97 + offset)}"
                for offset in range(3 + index % 2)
            ),
            truth=None,
            seed=seed + index * 47,
            external=True,
            out_of_grammar=True,
        )
        for index in range(count)
    ]


def run_primitive_invention_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_worlds: int = 24,
    transfer_worlds: int = 32,
    external_worlds: int = 12,
    novel_worlds: int = 12,
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
    parent_id = "procedure_typed_dsl_synthesis_0a203e5df940"
    runtime.skills.promote(
        ProcedureCandidate(
            procedure_id=parent_id,
            goal="primitive_invention_and_compression",
            steps=["phase44_typed_dsl_synthesis"],
            score=0.0,
            success=True,
            evidence={"evaluation": "phase44_dependency"},
        )
    )
    masks = _select_masks(8)
    learned_masks = masks[:4]
    novel_masks = masks[4:8]
    development_rows = []
    verified_uses: Dict[int, List[str]] = {}
    for index, world in enumerate(
        _worlds(
            development_worlds,
            seed=450_045,
            prefix="development",
            masks=learned_masks,
        )
    ):
        result = _induce(world, library_masks=None, seed=1_000 + index)
        exact = bool(
            result["accepted"]
            and result["program_id"] == world.truth.program_id
        )
        if exact:
            verified_uses.setdefault(
                world.truth.primitive_mask, []
            ).append(world.domain)
        development_rows.append(
            {
                "world_id": world.world_id,
                "exact": exact,
                "truth_id": world.truth.program_id,
                "result": result,
            }
        )
    promoted_masks = sorted(
        mask
        for mask, domains in verified_uses.items()
        if len(set(domains)) >= 3 and len(domains) >= 3
    )
    primitive_library = {}
    for mask in promoted_masks:
        uses = len(verified_uses[mask])
        raw_bits = uses * 6
        compressed_bits = 6 + uses * math.ceil(math.log2(max(2, len(promoted_masks))))
        primitive_library[str(mask)] = {
            "primitive_id": PrimitiveProgram(mask, 0, 1).primitive_id,
            "truth_table": list(_table_bits(mask)),
            "verified_uses": uses,
            "source_domains": sorted(set(verified_uses[mask])),
            "raw_description_bits": raw_bits,
            "compressed_description_bits": compressed_bits,
            "compression_gain_bits": raw_bits - compressed_bits,
        }
    worlds = (
        _worlds(
            transfer_worlds,
            seed=451_045,
            prefix="transfer",
            masks=promoted_masks,
        )
        + _worlds(
            external_worlds,
            seed=452_045,
            prefix="external",
            masks=promoted_masks,
            external=True,
        )
        + _worlds(
            novel_worlds,
            seed=453_045,
            prefix="novel",
            masks=novel_masks,
            external=True,
        )
        + _ood_worlds(ood_worlds, seed=454_045)
    )
    rows = []
    for index, world in enumerate(worlds):
        transfer = _induce(
            world,
            library_masks=promoted_masks,
            seed=3_000 + index,
        )
        cold = _induce(
            world,
            library_masks=None,
            seed=4_000 + index,
        )
        truth_id = world.truth.program_id if world.truth else None
        row = {
            "world_id": world.world_id,
            "domain": world.domain,
            "external": world.external,
            "out_of_grammar": world.out_of_grammar,
            "novel_primitive": bool(
                world.truth
                and world.truth.primitive_mask not in promoted_masks
            ),
            "truth": asdict(world.truth) if world.truth else None,
            "truth_id": truth_id,
            "base_dsl_inadequate": bool(
                world.truth
                and not _base_dsl_can_express(world.truth, world.arity)
            ),
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
        runtime.store.state["primitive_invention_sessions"].append(
            {
                "world_id": world.world_id,
                "status": transfer["status"],
                "primitive_id": transfer["primitive_id"],
                "surprise_fallback_at": transfer["surprise_fallback_at"],
                "verified": row["exact"] or row["safe_abstention"],
            }
        )
        rows.append(row)
    runtime.store.state["invented_primitives"] = primitive_library
    runtime.store.commit(reason="phase45_primitive_library")
    valid = [row for row in rows if not row["out_of_grammar"]]
    transferred = [row for row in valid if not row["novel_primitive"]]
    novel = [row for row in valid if row["novel_primitive"]]
    external = [
        row for row in transferred if row["external"]
    ]
    ood = [row for row in rows if row["out_of_grammar"]]
    transfer_trials = sum(
        row["transfer"]["environmental_trials"] for row in transferred
    ) / len(transferred)
    cold_trials = sum(
        row["cold"]["environmental_trials"] for row in transferred
    ) / len(transferred)
    novel_transfer_trials = sum(
        row["transfer"]["environmental_trials"] for row in novel
    ) / len(novel)
    novel_cold_trials = sum(
        row["cold"]["environmental_trials"] for row in novel
    ) / len(novel)
    gate = {
        "development_exact_accuracy": sum(
            int(row["exact"]) for row in development_rows
        ) / len(development_rows),
        "promoted_primitives": len(promoted_masks),
        "positive_compression_primitives": sum(
            int(row["compression_gain_bits"] > 0)
            for row in primitive_library.values()
        ),
        "transfer_exact_accuracy": sum(
            int(row["exact"]) for row in transferred
        ) / len(transferred),
        "external_exact_accuracy": sum(
            int(row["exact"]) for row in external
        ) / len(external),
        "novel_primitive_exact_accuracy": sum(
            int(row["exact"]) for row in novel
        ) / len(novel),
        "novel_surprise_fallback_rate": sum(
            int(row["transfer"]["surprise_fallback_at"] is not None)
            for row in novel
        ) / len(novel),
        "base_dsl_inadequacy_rate": sum(
            int(row["base_dsl_inadequate"]) for row in valid
        ) / len(valid),
        "safe_ood_abstention": sum(
            int(row["safe_abstention"]) for row in ood
        ) / len(ood),
        "unsafe_forced_primitives": sum(
            int(not row["safe_abstention"]) for row in ood
        ),
        "mean_transfer_trials": transfer_trials,
        "mean_cold_trials": cold_trials,
        "transfer_trial_reduction": 1.0 - transfer_trials / cold_trials,
        "novel_trial_overhead": (
            novel_transfer_trials / novel_cold_trials - 1.0
        ),
        "predictive_accuracy": sum(
            row["transfer"]["predictive_accuracy"] for row in valid
        ) / len(valid),
        "provenance_complete": sum(
            int(
                bool(row["transfer"]["trace"])
                and bool(row["transfer"]["confirmation"])
                and bool(row["transfer"]["audit"])
            )
            for row in rows
        ) / len(rows),
    }
    errors = []
    for name, minimum in (
        ("development_exact_accuracy", 0.90),
        ("transfer_exact_accuracy", 0.95),
        ("external_exact_accuracy", 0.90),
        ("novel_primitive_exact_accuracy", 0.90),
        ("base_dsl_inadequacy_rate", 0.95),
        ("safe_ood_abstention", 0.90),
        ("transfer_trial_reduction", 0.15),
        ("predictive_accuracy", 0.98),
        ("provenance_complete", 1.0),
    ):
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum:.2f}")
    if gate["promoted_primitives"] < 4:
        errors.append("FEWER_THAN_FOUR_PRIMITIVES_PROMOTED")
    if gate["positive_compression_primitives"] != gate["promoted_primitives"]:
        errors.append("PRIMITIVE_WITHOUT_POSITIVE_COMPRESSION")
    if gate["unsafe_forced_primitives"]:
        errors.append("UNSAFE_PRIMITIVE_FORCED")
    if gate["novel_trial_overhead"] > 0.25:
        errors.append("NOVEL_PRIMITIVE_FALLBACK_OVERHEAD_ABOVE_25_PERCENT")
    gate["accepted"] = not errors
    gate["errors"] = errors
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_primitive_invention_"
            + _canonical_hash(
                {"parent": parent_id, "gate": gate, "library": primitive_library}
            )[:12]
        ),
        goal="primitive_invention_and_compression",
        steps=[
            "reject_inadequate_phase44_program_language",
            "induce_unnamed_symmetric_predicate_truth_table",
            "compose_primitive_with_context_gate",
            "verify_recurrence_across_unrelated_domains",
            "promote_only_positive_description_length_compression",
            "transfer_primitive_as_reversible_search_prior",
            "neutralise_prior_on_posterior_surprise",
            "abstain_on_directed_relation_outside_invention_grammar",
        ],
        score=gate["transfer_exact_accuracy"] + gate["predictive_accuracy"],
        success=gate["accepted"],
        evidence={"evaluation": "phase45_sealed", "gate": gate},
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="phase45_primitive_invention")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "library_retained": len(
            restarted.store.state["invented_primitives"]
        ) == len(primitive_library),
        "sessions_retained": len(
            restarted.store.state["primitive_invention_sessions"]
        ) == len(rows),
        "champion_retained": (
            restarted.store.state["champions"].get(
                "primitive_invention_and_compression"
            ) == candidate.procedure_id
        ),
        "relearning_worlds": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and all(
            (
                restart["library_retained"],
                restart["sessions_retained"],
                restart["champion_retained"],
            )
        )
    )
    result = {
        "schema_version": "aion.hexcore.primitive_invention.v1",
        "benchmark": "typed_predicate_invention_and_library_compression",
        "passed": passed,
        "gate": gate,
        "primitive_library": primitive_library,
        "development": {"worlds": len(development_rows), "rows": development_rows},
        "sealed": {"worlds": len(rows), "rows": rows},
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "gold_isolation": {
            "solver_receives_truth_table": False,
            "solver_receives_variable_binding": False,
            "solver_receives_novel_or_ood_label": False,
            "gold_used_only_by_evaluator": True,
        },
        "boundary_statement": (
            "Phase 45 invents unnamed symmetric Boolean predicates by inducing "
            "six-cell truth tables over ternary variable pairs and composes "
            "them with optional context gates. Symmetry, arity, value domain, "
            "truth-table size, simulator and oracle remain engineered. This "
            "is not unrestricted operator invention, universal programming, "
            "real-world scientific discovery or AGI."
        ),
        "created_at": _utc_timestamp(),
    }
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run HexCore Phase 45 primitive invention.")
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--development-worlds", type=int, default=24)
    parser.add_argument("--transfer-worlds", type=int, default=32)
    parser.add_argument("--external-worlds", type=int, default=12)
    parser.add_argument("--novel-worlds", type=int, default=12)
    parser.add_argument("--ood-worlds", type=int, default=8)
    args = parser.parse_args()
    result = run_primitive_invention_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        development_worlds=args.development_worlds,
        transfer_worlds=args.transfer_worlds,
        external_worlds=args.external_worlds,
        novel_worlds=args.novel_worlds,
        ood_worlds=args.ood_worlds,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
