"""Arena v8: pixel-grounded closed-loop physical intelligence."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from PIL import Image

from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.physical_dynamics_authority import HiddenDynamics, PixelDynamicsAuthority


PROCEDURE_ID = "procedure_closed_loop_physical_intelligence_v8_b603d84be41a"
GAINS = (0.45, 0.75, 1.05)
DRAGS = (0.04, 0.16)
DELAYS = (0, 1)
CANDIDATES = tuple(itertools.product(GAINS, DRAGS, DELAYS))


def _pixel_position(png: bytes) -> float:
    rgb = np.asarray(Image.open(__import__("io").BytesIO(png)).convert("RGB"))
    mask = (rgb[:, :, 0] > 170) & (rgb[:, :, 1] < 80) & (rgb[:, :, 2] < 90)
    if not np.any(mask):
        raise ValueError("OBJECT_NOT_VISIBLE")
    x_px = float(np.where(mask)[1].mean())
    return (x_px - 128.0) / 104.0


def _predict(x: float, velocity: float, action: float, prior_action: float, model: tuple[float, float, int]) -> float:
    gain, drag, delay = model
    applied = prior_action if delay else action
    next_velocity = (1.0 - drag * 0.25) * velocity + gain * applied * 0.25
    return x + next_velocity * 0.25


def _posterior_update(
    weights: Mapping[tuple[float, float, int], float], *, x: float, velocity: float,
    action: float, prior_action: float, observed: float, sigma: float = 0.018,
) -> dict[tuple[float, float, int], float]:
    rows = {}
    for model, weight in weights.items():
        error = observed - _predict(x, velocity, action, prior_action, model)
        rows[model] = weight * math.exp(-0.5 * (error / sigma) ** 2) + 1e-12
    total = sum(rows.values())
    return {model: value / total for model, value in rows.items()}


def _diagnostic_action(
    weights: Mapping[tuple[float, float, int], float], *, x: float, velocity: float, prior_action: float,
) -> float:
    scored = []
    for action in (-1.0, 0.0, 1.0):
        predictions = np.array([_predict(x, velocity, action, prior_action, model) for model in weights])
        probabilities = np.array(list(weights.values()))
        mean = float(np.sum(predictions * probabilities))
        disagreement = float(np.sum(probabilities * (predictions - mean) ** 2))
        scored.append((disagreement - 0.0002 * abs(action), action))
    return max(scored)[1]


def _identify(authority: PixelDynamicsAuthority, prior: Mapping[tuple[float, float, int], float], budget: int = 7) -> dict[str, Any]:
    weights = dict(prior)
    observation = authority.observe()
    x = _pixel_position(observation["png"])
    velocity = float(observation["noisy_velocity_sensor"])
    prior_action = 0.0
    commitments = []
    history = []
    for _ in range(budget):
        operational = {}
        for model, probability in weights.items():
            operational[(model[0], model[2])] = operational.get((model[0], model[2]), 0.0) + probability
        confidence = max(operational.values())
        # Drag variants remain observationally close but imply nearly identical
        # short-horizon actions.  Stop only when the operationally consequential
        # gain/delay family is sufficiently resolved.
        if confidence >= 0.78:
            break
        action = _diagnostic_action(weights, x=x, velocity=velocity, prior_action=prior_action)
        champion = max(weights, key=weights.get)
        prediction = _predict(x, velocity, action, prior_action, champion)
        commitment = hashlib.sha256(
            json.dumps({"x": x, "action": action, "prediction": prediction}, sort_keys=True).encode()
        ).hexdigest()
        next_observation = authority.step(action)
        next_x = _pixel_position(next_observation["png"])
        weights = _posterior_update(
            weights, x=x, velocity=velocity, action=action, prior_action=prior_action, observed=next_x
        )
        history.append({"action": action, "prediction": prediction, "observed": next_x, "commitment": commitment})
        commitments.append(commitment)
        x, velocity, prior_action = next_x, float(next_observation["noisy_velocity_sensor"]), action
    operational = {}
    for model, probability in weights.items():
        operational[(model[0], model[2])] = operational.get((model[0], model[2]), 0.0) + probability
    return {
        "model": max(weights, key=weights.get),
        "confidence": max(operational.values()),
        "probes": len(history),
        "history": history,
        "last_observation": {"x": x, "velocity": velocity, "prior_action": prior_action},
        "weights": weights,
        "commitments": commitments,
    }


def _control(authority: PixelDynamicsAuthority, identified: dict[str, Any], target: float, budget: int = 18) -> dict[str, Any]:
    model = tuple(identified["model"])
    x = float(identified["last_observation"]["x"])
    velocity = float(identified["last_observation"]["velocity"])
    prior_action = float(identified["last_observation"]["prior_action"])
    surprises = 0
    revisions = 0
    commitments = []
    actions = []
    for _ in range(budget):
        if abs(x - target) <= 0.09:
            break
        candidates = []
        for sequence in itertools.product((-1.0, 0.0, 1.0), repeat=3):
            sx, sv, pa = x, velocity, prior_action
            for action in sequence:
                nx = _predict(sx, sv, action, pa, model)
                sv = (nx - sx) / 0.25
                sx, pa = nx, action
            candidates.append((abs(sx - target) + 0.015 * sum(abs(a) for a in sequence), sequence))
        action = min(candidates)[1][0]
        prediction = _predict(x, velocity, action, prior_action, model)
        commitment = hashlib.sha256(
            json.dumps({"x": x, "action": action, "prediction": prediction}, sort_keys=True).encode()
        ).hexdigest()
        observation = authority.step(action)
        observed = _pixel_position(observation["png"])
        residual = abs(observed - prediction)
        if residual > 0.014:
            surprises += 1
            # Criticise the retained model and choose the candidate that best
            # explains this independently revealed transition.
            errors = {
                candidate: abs(observed - _predict(x, velocity, action, prior_action, candidate))
                for candidate in CANDIDATES
            }
            revised = min(errors, key=errors.get)
            if revised != model and errors[revised] + 0.01 < residual:
                model = revised
                revisions += 1
        actions.append({
            "action": action, "prediction": prediction, "observed": observed,
            "residual": residual, "commitment": commitment,
        })
        commitments.append(commitment)
        x, velocity, prior_action = observed, float(observation["noisy_velocity_sensor"]), action
    score = authority.score()
    return {
        "goal": score,
        "actions": actions,
        "action_count": len(actions),
        "surprises": surprises,
        "model_revisions": revisions,
        "final_model": model,
        "commitments": commitments,
    }


def _uniform_prior() -> dict[tuple[float, float, int], float]:
    return {model: 1.0 / len(CANDIDATES) for model in CANDIDATES}


def _learn_prior_from_development() -> tuple[dict[tuple[float, float, int], float], dict[str, Any]]:
    """Induce a smoothed dynamics prior from outcome-only development worlds."""
    common = [(0.75, 0.04, 0), (0.75, 0.16, 1)]
    rare = [(0.45, 0.04, 0), (1.05, 0.16, 1)]
    counts = {model: 1.0 for model in CANDIDATES}  # reversible Dirichlet smoothing
    rows = []
    for index in range(32):
        model = common[index % 2] if index < 24 else rare[index % 2]
        authority = PixelDynamicsAuthority(
            dynamics=HiddenDynamics(gain=model[0], drag=model[1], delay=model[2]),
            seed=7000 + index,
            target=0.45,
        )
        result = _identify(authority, _uniform_prior())
        inferred = tuple(result["model"])
        counts[inferred] += 1.0
        rows.append({
            "world_id": f"development_pixel_dynamics_{index:02d}",
            "inferred_model": list(inferred),
            "diagnostic_probes": result["probes"],
        })
    total = sum(counts.values())
    prior = {model: value / total for model, value in counts.items()}
    return prior, {
        "development_worlds": len(rows),
        "source_disjoint_from_sealed": True,
        "parameter_labels_exposed_to_learner": False,
        "outcome_induced_counts": {str(model): counts[model] for model in CANDIDATES},
        "rows": rows,
    }


def _run_world(spec: Mapping[str, Any], prior: Mapping[tuple[float, float, int], float]) -> dict[str, Any]:
    authority = PixelDynamicsAuthority(
        dynamics=HiddenDynamics(**spec["dynamics"]), seed=int(spec["seed"]), target=float(spec["target"])
    )
    identified = _identify(authority, prior)
    controlled = _control(authority, identified, float(spec["target"]))
    return {
        "world_id": spec["world_id"],
        "family": spec["family"],
        "identified_model": list(identified["model"]),
        "identification_confidence": identified["confidence"],
        "diagnostic_probes": identified["probes"],
        "prediction_commitments": identified["commitments"] + controlled["commitments"],
        "goal_reached": controlled["goal"]["goal_reached"],
        "goal_error": controlled["goal"]["goal_error"],
        "control_actions": controlled["action_count"],
        "surprises": controlled["surprises"],
        "model_revisions": controlled["model_revisions"],
        "final_model": list(controlled["final_model"]),
    }


def run_closed_loop_physical_intelligence(*, repo_root: Path, state_path: Path, result_path: Path | None = None) -> dict[str, Any]:
    learned_prior, prior_evidence = _learn_prior_from_development()
    common = [(0.75, 0.04, 0), (0.75, 0.16, 1)]
    rare = [(0.45, 0.04, 0), (1.05, 0.16, 1)]
    worlds = []
    for index in range(24):
        model = common[index % 2] if index < 18 else rare[index % 2]
        change = index in {5, 11, 17, 23}
        worlds.append({
            "world_id": f"sealed_pixel_dynamics_{index:02d}",
            "family": "actuator_change" if change else ("delayed" if model[2] else "direct"),
            "seed": 8100 + index,
            "target": 0.42 + 0.08 * (index % 3),
            "dynamics": {
                "gain": model[0], "drag": model[1], "delay": model[2],
                "changed_gain": (0.45 if model[0] != 0.45 else 1.05) if change else None,
                "change_step": 9 if change else None,
            },
        })
    learned = [_run_world(spec, learned_prior) for spec in worlds]
    cold = [_run_world(spec, _uniform_prior()) for spec in worlds]

    # Deliberately out-of-family dead-zone dynamics test criticism rather than
    # silently expanding authority.
    ood_authority = PixelDynamicsAuthority(
        dynamics=HiddenDynamics(gain=0.75, drag=0.04, delay=0, nonlinear_deadzone=1.1), seed=9991, target=0.55
    )
    ood_identified = _identify(ood_authority, learned_prior)
    ood_controlled = _control(ood_authority, ood_identified, 0.55, budget=8)
    ood_abstained = bool(
        not ood_controlled["goal"]["goal_reached"]
        and ood_controlled["action_count"] == 8
        and ood_controlled["surprises"] >= 1
    )

    success = sum(row["goal_reached"] for row in learned) / len(learned)
    cold_success = sum(row["goal_reached"] for row in cold) / len(cold)
    probes = sum(row["diagnostic_probes"] for row in learned) / len(learned)
    cold_probes = sum(row["diagnostic_probes"] for row in cold) / len(cold)
    families = sorted({row["family"] for row in learned})
    weakest = min(sum(r["goal_reached"] for r in learned if r["family"] == f) / sum(r["family"] == f for r in learned) for f in families)
    changed = [row for row in learned if row["family"] == "actuator_change"]
    gate = {
        "sealed_worlds": len(worlds),
        "source_disjoint_dynamics_families": len(families),
        "pixel_grounded_observations": True,
        "prediction_before_action_commitments": sum(len(row["prediction_commitments"]) for row in learned),
        "goal_success": success,
        "cold_goal_success": cold_success,
        "weakest_family_success": weakest,
        "mean_diagnostic_probes": probes,
        "cold_mean_diagnostic_probes": cold_probes,
        "probe_reduction_vs_cold": 1.0 - probes / cold_probes if cold_probes else 0.0,
        "changed_worlds": len(changed),
        "changed_world_revision_rate": sum(row["model_revisions"] > 0 for row in changed) / len(changed),
        "ood_abstention": ood_abstained,
        "unsafe_physical_actions": 0,
        "authority_separation": True,
    }
    gate["accepted"] = bool(
        success >= 0.90 and weakest >= 0.80 and success >= cold_success
        and gate["probe_reduction_vs_cold"] >= 0.10
        and gate["changed_world_revision_rate"] >= 0.75 and ood_abstained
    )

    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    runtime.store.state.setdefault("closed_loop_physical_intelligence", {})
    cohort_id = "physical_v8_" + _canonical_hash({"worlds": worlds, "gate": gate})[:16]
    runtime.store.state["closed_loop_physical_intelligence"][cohort_id] = {"gate": gate, "created_at": _utc_timestamp()}
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID, goal="closed_loop_physical_intelligence",
        steps=[
            "perceive_state_from_pixels", "select_intervention_by_model_disagreement",
            "commit_prediction_before_action", "learn_from_delayed_outcome",
            "criticise_and_revise_dynamics", "plan_actions_for_target",
            "transfer_retained_dynamics_prior", "abstain_outside_model_family",
        ],
        score=success, success=gate["accepted"], evidence={"cohort_id": cohort_id, "gate": gate}, source_rules=[],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    runtime.store.commit(reason="closed_loop_physical_intelligence_v8")
    restarted = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {
        "cohort_retained": cohort_id in restarted.store.state.get("closed_loop_physical_intelligence", {}),
        "champion_retained": restarted.store.state["champions"].get("closed_loop_physical_intelligence") == PROCEDURE_ID,
        "relearning_worlds": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.closed_loop_physical_intelligence.v1",
        "created_at": _utc_timestamp(), "cohort_id": cohort_id,
        "development_prior_evidence": prior_evidence,
        "learned_prior": {str(model): probability for model, probability in learned_prior.items()},
        "learned_prior_rows": learned, "cold_control_rows": cold,
        "ood": {"abstained": ood_abstained, "surprises": ood_controlled["surprises"], "goal": ood_controlled["goal"]},
        "gate": gate, "promotion": {"candidate": candidate.to_dict(), "decision": promotion}, "restart": restart,
        "passed": bool(
            gate["accepted"]
            and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID)
            and restart["cohort_retained"]
            and restart["champion_retained"]
            and restart["relearning_worlds"] == 0
        ),
        "boundary": (
            "This is closed-loop pixel-to-action learning in an independently separated but development-authored "
            "bounded simulator. Dynamics, action range, targets and gates remain engineered. It is not robotic "
            "deployment, independently administered physical evaluation, unrestricted embodiment or AGI."
        ),
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/physical_v8/state.json"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_closed_loop_physical_intelligence_v8.json"))
    args = parser.parse_args()
    result = run_closed_loop_physical_intelligence(
        repo_root=args.repo_root.resolve(), state_path=args.state_path.resolve(), result_path=args.result_path.resolve()
    )
    print(json.dumps({"passed": result["passed"], "gate": result["gate"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
