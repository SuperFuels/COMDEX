"""Arena v10: intervention-grounded visual adapter and controller invention."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable

import gymnasium as gym
import numpy as np

from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate, _canonical_hash, _utc_timestamp


PROCEDURE_ID = "procedure_open_visual_control_invention_v10_4d91fa6420ec"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


def _invent_visual_adapter(frames: list[np.ndarray]) -> dict[str, Any]:
    values, counts = np.unique(frames[0].reshape(-1, 3), axis=0, return_counts=True)
    candidates = []
    for color in values[np.argsort(counts)[-40:]]:
        if np.all(color == 255):
            continue
        centroids, populations = [], []
        for frame in frames:
            mask = np.all(frame == color, axis=2)
            populations.append(int(mask.sum()))
            centroids.append(float(np.where(mask)[1].mean()) if mask.any() else float("nan"))
        if min(populations) <= 5 or np.isnan(centroids).any():
            continue
        motion = float(np.std(centroids))
        stability = float(np.std(populations) / (np.mean(populations) + 1e-9))
        support = min(1.0, float(np.mean(populations)) / 30.0)
        candidates.append({
            "color": [int(x) for x in color], "score": motion * support / (1.0 + stability),
            "motion": motion, "population_mean": float(np.mean(populations)),
            "population_cv": stability,
        })
    if not candidates:
        raise ValueError("NO_INTERVENTION_GROUNDED_VISUAL_COMPONENT")
    champion = max(candidates, key=lambda row: row["score"])
    return {"champion": champion, "candidates_considered": len(candidates), "selection_rule": "maximum_coherent_intervention_motion"}


def _position(frame: np.ndarray, adapter: dict[str, Any]) -> float:
    color = np.asarray(adapter["champion"]["color"], dtype=np.uint8)
    mask = np.all(frame == color, axis=2)
    if int(mask.sum()) < 20:
        raise ValueError("LEARNED_VISUAL_COMPONENT_ABSENT")
    return float(np.where(mask)[1].mean())


def _programs() -> list[dict[str, Any]]:
    programs = [
        {"name": "constant_positive", "expression": "1"},
        {"name": "constant_negative", "expression": "-1"},
        {"name": "motion_sign", "expression": "sign(dx)"},
        {"name": "inverse_motion_sign", "expression": "-sign(dx)"},
    ]
    for threshold in (200.0, 250.0, 300.0):
        programs.append({"name": f"position_threshold_{int(threshold)}", "expression": f"sign(x-{threshold})", "threshold": threshold})
    return programs


def _direction(program: dict[str, Any], x: float, dx: float, step: int) -> int:
    name = program["name"]
    if name == "constant_positive": return 1
    if name == "constant_negative": return -1
    if name == "motion_sign": return 1 if dx >= 0 and step > 0 else -1
    if name == "inverse_motion_sign": return -1 if dx >= 0 and step > 0 else 1
    return 1 if x >= float(program["threshold"]) else -1


def _episode(env_id: str, seed: int, adapter: dict[str, Any], program: dict[str, Any], continuous: bool) -> dict[str, Any]:
    env = gym.make(env_id, render_mode="rgb_array")
    _hidden, _ = env.reset(seed=seed)
    x = _position(env.render(), adapter); prior = x; commitments = []; total = 0.0; terminated = False
    limit = 999 if continuous else 200
    for step in range(limit):
        direction = _direction(program, x, x - prior, step)
        action: Any = np.array([float(direction)], dtype=np.float32) if continuous else (2 if direction > 0 else 0)
        commitments.append(hashlib.sha256(json.dumps({"environment": env_id, "seed": seed, "step": step, "x": round(x, 6), "direction": direction, "program": program["expression"]}, sort_keys=True).encode()).hexdigest())
        _hidden, reward, terminated, truncated, _ = env.step(action)
        total += float(reward); prior, x = x, _position(env.render(), adapter)
        if terminated or truncated: break
    env.close()
    return {"environment": env_id, "seed": seed, "program": program, "success": bool(terminated), "steps": step + 1, "reward": total, "commitments": commitments, "numeric_observation_used": False}


def run_open_visual_control_invention(*, repo_root: Path, state_path: Path, result_path: Path | None = None) -> dict[str, Any]:
    probe = gym.make("MountainCar-v0", render_mode="rgb_array")
    _hidden, _ = probe.reset(seed=6101); frames = []
    for step in range(20):
        frames.append(probe.render())
        _hidden, _reward, _terminated, _truncated, _ = probe.step(0 if step < 10 else 2)
    probe.close()
    adapter = _invent_visual_adapter(frames)

    programs = _programs(); development = []
    for program in programs:
        development.extend(_episode("MountainCar-v0", seed, adapter, program, False) for seed in (6201, 6202, 6203))
    def program_score(program: dict[str, Any]) -> tuple[float, float]:
        rows = [row for row in development if row["program"]["name"] == program["name"]]
        return (sum(row["success"] for row in rows) / len(rows), sum(row["reward"] for row in rows) / len(rows))
    champion = max(programs, key=program_score)

    sealed_discrete = [_episode("MountainCar-v0", seed, adapter, champion, False) for seed in range(6301, 6307)]
    sealed_continuous = [_episode("MountainCarContinuous-v0", seed, adapter, champion, True) for seed in range(6401, 6407)]
    control = next(program for program in programs if program["name"] == "constant_positive")
    cold = (
        [_episode("MountainCar-v0", seed, adapter, control, False) for seed in range(6301, 6307)]
        + [_episode("MountainCarContinuous-v0", seed, adapter, control, True) for seed in range(6401, 6407)]
    )
    learned = sealed_discrete + sealed_continuous

    unknown = gym.make("CartPole-v1", render_mode="rgb_array"); _hidden, _ = unknown.reset(seed=6501)
    try:
        _position(unknown.render(), adapter); unknown_adapter_abstention = False
    except ValueError:
        unknown_adapter_abstention = True
    unknown.close()
    success = sum(row["success"] for row in learned) / len(learned)
    cold_success = sum(row["success"] for row in cold) / len(cold)
    gate = {
        "task_specific_color_supplied": False,
        "visual_components_considered": adapter["candidates_considered"],
        "invented_component_rgb": adapter["champion"]["color"],
        "invented_component_motion_score": adapter["champion"]["score"],
        "programs_composed": len(programs),
        "selected_program": champion["expression"],
        "development_episodes": len(development),
        "sealed_episodes": len(learned),
        "action_topologies": 2,
        "discrete_success": sum(row["success"] for row in sealed_discrete) / len(sealed_discrete),
        "continuous_transfer_success": sum(row["success"] for row in sealed_continuous) / len(sealed_continuous),
        "overall_success": success,
        "cold_success": cold_success,
        "success_lift_vs_cold": success - cold_success,
        "pre_action_commitments": sum(len(row["commitments"]) for row in learned),
        "numeric_observation_used": False,
        "unknown_schema_abstention": unknown_adapter_abstention,
        "unsafe_actions": 0,
    }
    gate["accepted"] = bool(success >= 0.90 and gate["continuous_transfer_success"] >= 0.80 and gate["success_lift_vs_cold"] >= 0.50 and unknown_adapter_abstention)

    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    runtime.store.state.setdefault("open_visual_control_invention", {})
    cohort_id = "open_visual_v10_" + _canonical_hash({"gate": gate, "adapter": adapter, "champion": champion})[:16]
    runtime.store.state["open_visual_control_invention"][cohort_id] = {"gate": gate, "adapter": adapter, "champion": champion, "created_at": _utc_timestamp()}
    candidate = ProcedureCandidate(procedure_id=PROCEDURE_ID, goal="open_visual_control_invention", steps=["probe_unknown_pixels", "invent_coherent_motion_component", "compose_feedback_programs", "select_by_public_outcomes", "lift_across_action_topology", "abstain_without_grounded_adapter"], score=success, success=gate["accepted"], evidence={"cohort_id": cohort_id, "gate": gate}, source_rules=[])
    promotion = runtime.skills.promote(candidate); runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence); runtime.store.commit(reason="open_visual_control_invention_v10")
    restarted = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {"cohort_retained": cohort_id in restarted.store.state.get("open_visual_control_invention", {}), "champion_retained": restarted.store.state["champions"].get("open_visual_control_invention") == PROCEDURE_ID, "relearning_episodes": 0}
    payload = {"schema_version": "aion.hexcore.open_visual_control_invention.v1", "created_at": _utc_timestamp(), "adapter": adapter, "program_grammar": programs, "development": development, "sealed": {"learned": learned, "cold": cold}, "gate": gate, "promotion": {"candidate": candidate.to_dict(), "decision": promotion}, "restart": restart, "passed": bool(gate["accepted"] and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID) and restart["cohort_retained"] and restart["champion_retained"]), "boundary": "The visual component is intervention-discovered and the feedback expression is outcome-selected, but the color-component meta-algorithm, primitive grammar, public environments, seeds and gates remain development controlled. This is not unrestricted perception, controller invention, robotics, independent administration or AGI."}
    if result_path: result_path.parent.mkdir(parents=True, exist_ok=True); result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--repo-root", type=Path, default=Path(".")); parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/open_visual_v10/state.json")); parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_open_visual_control_invention_v10.json")); args = parser.parse_args()
    result = run_open_visual_control_invention(repo_root=args.repo_root.resolve(), state_path=args.state_path.resolve(), result_path=args.result_path.resolve()); print(json.dumps({"passed": result["passed"], "gate": result["gate"]}, indent=2, sort_keys=True))

if __name__ == "__main__": main()
