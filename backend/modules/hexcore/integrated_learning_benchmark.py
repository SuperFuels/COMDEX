from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence

from backend.modules.hexcore.persistent_learning import (
    EvidenceCapsule,
    HexCorePersistentLearningRuntime,
    TransitionObservation,
)


WORLD_ID = "lumen_vault_v1"
GOAL = "opened=True"


class LumenVault:
    """Small deterministic domain whose dynamics are not given to the learner."""

    def __init__(self, *, threshold: int = 4, start_energy: int = 0) -> None:
        self.threshold = threshold
        self.start_energy = start_energy

    def transition(self, state: Mapping[str, Any], action: str) -> Dict[str, Any]:
        next_state = dict(state)
        energy = int(next_state.get("energy") or 0)
        if action == "charge":
            next_state["energy"] = energy + 2
        elif action == "leak":
            next_state["energy"] = max(0, energy - 1)
        elif action == "open":
            next_state["opened"] = energy >= self.threshold
        return next_state

    def run(self, steps: Sequence[str], *, start_energy: int | None = None) -> Dict[str, Any]:
        state: Dict[str, Any] = {
            "energy": self.start_energy if start_energy is None else int(start_energy),
            "opened": False,
        }
        trace = []
        for action in steps:
            before = dict(state)
            state = self.transition(state, action)
            trace.append({"state": before, "action": action, "next_state": dict(state)})
            if state["opened"]:
                break
        success = bool(state["opened"])
        score = (1.0 if success else 0.0) - (0.03 * len(trace))
        return {
            "success": success,
            "score": round(max(0.0, score), 6),
            "final_state": state,
            "trace": trace,
        }


def _allow_authority(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "source": "integrated_benchmark_authority",
        "goal": goal,
        "S": 1.0,
        "H": 0.0,
    }


def _observation(
    *,
    observation_id: str,
    state: Dict[str, Any],
    action: str,
    next_state: Dict[str, Any],
) -> TransitionObservation:
    return TransitionObservation(
        observation_id=observation_id,
        world_id=WORLD_ID,
        state=state,
        action=action,
        next_state=next_state,
        evidence_id=f"simulator:{observation_id}",
    )


def run_benchmark(*, state_path: Path, result_path: Path | None = None) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()

    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow_authority,
    )
    world = LumenVault()

    baseline = {
        "knowledge_correct": False,
        "active_world_rule_count": 0,
        "task_success": False,
        "composite_score": 0.0,
    }

    # ------------------------------------------------------------------
    # Knowledge learning: an older rule is superseded by a newer source.
    # ------------------------------------------------------------------
    old_manual = EvidenceCapsule(
        capsule_id="capsule_lumen_manual_r1",
        source_uri="lumen://manual/revision-1",
        content="An early manual states that the vault requires five energy units.",
        claims=[
            {
                "subject": "lumen_vault",
                "predicate": "minimum_energy",
                "object": "5",
                "revision": 1,
                "confidence": 0.80,
            }
        ],
    )
    revised_manual = EvidenceCapsule(
        capsule_id="capsule_lumen_manual_r2",
        source_uri="lumen://manual/revision-2",
        content="The corrected manual states that the vault requires four energy units.",
        claims=[
            {
                "subject": "lumen_vault",
                "predicate": "minimum_energy",
                "object": "4",
                "revision": 2,
                "confidence": 1.0,
            },
            {
                "subject": "lumen_vault",
                "predicate": "success_state",
                "object": "opened",
                "revision": 1,
                "confidence": 1.0,
            },
        ],
    )
    old_ingest = runtime.knowledge.ingest(old_manual)
    revised_ingest = runtime.knowledge.ingest(revised_manual)
    threshold_query = runtime.knowledge.query_claim("lumen_vault", "minimum_energy")
    retrieval = runtime.knowledge.retrieve("What minimum energy opens the lumen vault?")

    # ------------------------------------------------------------------
    # World learning: observe consequences without supplying action rules.
    # ------------------------------------------------------------------
    probes = [
        ({"energy": 0, "opened": False}, "charge"),
        ({"energy": 2, "opened": False}, "charge"),
        ({"energy": 1, "opened": False}, "charge"),
        ({"energy": 3, "opened": False}, "leak"),
        ({"energy": 1, "opened": False}, "leak"),
        ({"energy": 0, "opened": False}, "open"),
        ({"energy": 2, "opened": False}, "open"),
        ({"energy": 4, "opened": False}, "open"),
        ({"energy": 6, "opened": False}, "open"),
    ]
    for index, (state, action) in enumerate(probes, start=1):
        runtime.world.observe(
            _observation(
                observation_id=f"lumen_probe_{index}",
                state=state,
                action=action,
                next_state=world.transition(state, action),
            )
        )

    effect_rules = runtime.world.infer_effect_rules(world_id=WORLD_ID)
    threshold_rule = runtime.world.infer_threshold_rule(
        world_id=WORLD_ID,
        action="open",
        condition_field="energy",
        outcome_field="opened",
        success_value=True,
    )
    active_rules = runtime.world.active_rules(WORLD_ID)

    # ------------------------------------------------------------------
    # Skill learning: assemble a procedure from learned rules, verify it,
    # and promote it only when it outperforms the empty baseline.
    # ------------------------------------------------------------------
    candidate = runtime.skills.plan_threshold_goal(
        world_id=WORLD_ID,
        start_state={"energy": 0, "opened": False},
        terminal_action="open",
    )
    if candidate is None:
        raise RuntimeError("world learner did not produce enough structure to plan")
    evaluated = runtime.skills.evaluate(candidate, runner=world.run)
    promotion = runtime.skills.promote(evaluated)
    runtime.skills.record_outcome(
        procedure_id=evaluated.procedure_id,
        success=evaluated.success,
        score=evaluated.score,
        evidence=evaluated.evidence,
    )

    learned_score = (
        int(threshold_query.get("claim", {}).get("object") == "4")
        + int(bool(threshold_rule and threshold_rule.get("condition", {}).get("value") == 4.0))
        + int(evaluated.success)
    ) / 3.0

    # ------------------------------------------------------------------
    # Restart test: create a new runtime instance and solve a held-out
    # initial state without repeating ingestion, probes, or training.
    # ------------------------------------------------------------------
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow_authority,
    )
    retained_claim = restarted.knowledge.query_claim("lumen_vault", "minimum_energy")
    retained_champion = restarted.skills.champion(GOAL)
    restart_result = (
        world.run(retained_champion["steps"], start_energy=1)
        if retained_champion
        else {"success": False, "score": 0.0, "trace": []}
    )
    restart_rules = restarted.world.active_rules(WORLD_ID)

    after = {
        "knowledge_correct": retained_claim.get("claim", {}).get("object") == "4",
        "active_world_rule_count": len(restart_rules),
        "task_success": bool(restart_result["success"]),
        "composite_score": round(learned_score, 6),
    }

    result = {
        "schema_version": "aion.hexcore.integrated_learning_benchmark.v1",
        "benchmark": "lumen_vault_persistent_learning",
        "language_provider_used": False,
        "representation_model_required": False,
        "baseline": baseline,
        "after_learning": after,
        "improvement_delta": round(after["composite_score"] - baseline["composite_score"], 6),
        "knowledge": {
            "old_ingest": old_ingest,
            "revised_ingest": revised_ingest,
            "selected_claim": threshold_query.get("claim"),
            "retrieval_top_claim": retrieval[0]["claim"] if retrieval else None,
            "contradiction_resolved": bool(
                revised_ingest.get("superseded_claim_ids")
                and threshold_query.get("claim", {}).get("object") == "4"
            ),
            "provenance_complete": bool(threshold_query.get("provenance_complete")),
        },
        "world": {
            "probe_count_cycle_1": len(probes),
            "probe_count_cycle_2": 0,
            "effect_rules": effect_rules,
            "threshold_rule": threshold_rule,
            "active_rule_count": len(active_rules),
        },
        "skill": {
            "candidate": evaluated.to_dict(),
            "promotion": promotion,
            "retained_after_restart": retained_champion is not None,
            "held_out_restart_result": restart_result,
        },
        "persistence": {
            "state_path": str(state_path),
            "restart_revision": restarted.store.state["revision"],
            "knowledge_retained": retained_claim.get("claim", {}).get("object") == "4",
            "world_rules_retained": bool(restart_rules),
            "procedure_retained": retained_champion is not None,
            "second_cycle_required_relearning": False,
        },
        "status": restarted.status(),
        "gates": {
            "knowledge_gate": after["knowledge_correct"],
            "world_rule_gate": bool(threshold_rule and len(active_rules) >= 2),
            "skill_gate": evaluated.success and promotion.get("promoted") is True,
            "restart_gate": bool(
                restart_result["success"]
                and retained_champion
                and restart_rules
                and retained_claim.get("claim", {}).get("object") == "4"
            ),
        },
        "boundary_statement": (
            "This benchmark demonstrates bounded, governed, persistent learning across "
            "knowledge, world and skill layers. It is not evidence of general or frontier intelligence."
        ),
    }
    result["passed"] = all(result["gates"].values())

    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path("data/hexcore/integrated_learning_state.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_integrated_learning_benchmark.json"),
    )
    args = parser.parse_args()
    result = run_benchmark(state_path=args.state_path, result_path=args.result_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
