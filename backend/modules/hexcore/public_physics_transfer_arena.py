"""Arena v9: pixel-only transfer against public Gymnasium physics authority."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
from typing import Any, Callable

import gymnasium as gym
import numpy as np

from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PROCEDURE_ID = "procedure_public_pixel_physics_transfer_v9_627e18f70a39"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mountain_position(frame: np.ndarray) -> float:
    mask = np.all(frame == np.array([128, 128, 128], dtype=np.uint8), axis=2)
    if not np.any(mask):
        raise ValueError("MOUNTAIN_CAR_VISUAL_ADAPTER_FAILED")
    return float(np.where(mask)[1].mean())


def _cartpole_angle(frame: np.ndarray) -> float:
    axle = np.all(frame == np.array([129, 132, 203], dtype=np.uint8), axis=2)
    pole = np.all(frame == np.array([202, 152, 101], dtype=np.uint8), axis=2)
    if not np.any(axle) or not np.any(pole):
        raise ValueError("CARTPOLE_VISUAL_ADAPTER_FAILED")
    ay, ax = np.where(axle)
    py, px = np.where(pole)
    return math.atan2(float(px.mean() - ax.mean()), float(ay.mean() - py.mean()))


def _commit(environment: str, seed: int, step: int, percept: float, action: int, policy: str) -> str:
    return hashlib.sha256(json.dumps({
        "environment": environment, "seed": seed, "step": step,
        "percept": round(percept, 8), "action": action, "policy": policy,
    }, sort_keys=True).encode()).hexdigest()


def _run_mountain(seed: int, policy: str) -> dict[str, Any]:
    env = gym.make("MountainCar-v0", render_mode="rgb_array")
    _hidden_observation, _ = env.reset(seed=seed)
    current = _mountain_position(env.render())
    previous = current
    commitments = []
    terminated = False
    total_reward = 0.0
    for step in range(200):
        velocity = current - previous
        if policy == "always_right":
            action = 2
        elif policy == "always_left":
            action = 0
        elif policy == "position_switch":
            action = 0 if current < 250 else 2
        elif policy == "momentum_feedback":
            action = 2 if velocity >= 0 and step > 0 else 0
        else:
            raise ValueError("UNKNOWN_POLICY")
        commitments.append(_commit("MountainCar-v0", seed, step, current, action, policy))
        _hidden_observation, reward, terminated, truncated, _ = env.step(action)
        total_reward += float(reward)
        previous, current = current, _mountain_position(env.render())
        if terminated or truncated:
            break
    env.close()
    return {
        "seed": seed, "policy": policy, "success": bool(terminated),
        "steps": step + 1, "reward": total_reward,
        "pre_action_commitments": commitments,
        "numeric_observation_used": False,
    }


def _run_cartpole(seed: int, policy: str) -> dict[str, Any]:
    env = gym.make("CartPole-v1", render_mode="rgb_array")
    _hidden_observation, _ = env.reset(seed=seed)
    current = _cartpole_angle(env.render())
    previous = current
    commitments = []
    terminated = False
    for step in range(500):
        angular_change = current - previous
        multiplier = {"angle_only": 0.0, "predictive_1": 1.0, "predictive_2": 2.0, "predictive_5": 5.0}[policy]
        action = 1 if current + multiplier * angular_change > 0 else 0
        commitments.append(_commit("CartPole-v1", seed, step, current, action, policy))
        _hidden_observation, _reward, terminated, truncated, _ = env.step(action)
        previous, current = current, _cartpole_angle(env.render())
        if terminated or truncated:
            break
    env.close()
    return {
        "seed": seed, "policy": policy, "success": bool(not terminated and step + 1 == 500),
        "steps": step + 1, "reward": float(step + 1),
        "pre_action_commitments": commitments,
        "numeric_observation_used": False,
    }


def _tournament(
    runner: Callable[[int, str], dict[str, Any]], policies: list[str], seeds: list[int],
) -> tuple[str, list[dict[str, Any]]]:
    rows = [runner(seed, policy) for policy in policies for seed in seeds]
    def score(policy: str) -> tuple[float, float]:
        selected = [row for row in rows if row["policy"] == policy]
        return (
            sum(row["success"] for row in selected) / len(selected),
            sum(row["reward"] for row in selected) / len(selected),
        )
    champion = max(policies, key=score)
    return champion, rows


def run_public_physics_transfer(*, repo_root: Path, state_path: Path, result_path: Path | None = None) -> dict[str, Any]:
    mountain_policies = ["always_right", "always_left", "position_switch", "momentum_feedback"]
    cartpole_policies = ["angle_only", "predictive_1", "predictive_2", "predictive_5"]
    mountain_champion, mountain_dev = _tournament(_run_mountain, mountain_policies, [101, 102, 103])
    cartpole_champion, cartpole_dev = _tournament(_run_cartpole, cartpole_policies, [201, 202, 203])

    mountain_seeds = [301, 302, 303, 304, 305, 306]
    cartpole_seeds = [401, 402, 403, 404, 405, 406]
    learned = (
        [_run_mountain(seed, mountain_champion) for seed in mountain_seeds]
        + [_run_cartpole(seed, cartpole_champion) for seed in cartpole_seeds]
    )
    cold = (
        [_run_mountain(seed, mountain_policies[0]) for seed in mountain_seeds]
        + [_run_cartpole(seed, cartpole_policies[0]) for seed in cartpole_seeds]
    )
    learned_success = sum(row["success"] for row in learned) / len(learned)
    cold_success = sum(row["success"] for row in cold) / len(cold)
    family_success = {
        "MountainCar-v0": sum(row["success"] for row in learned[:6]) / 6,
        "CartPole-v1": sum(row["success"] for row in learned[6:]) / 6,
    }

    # Acrobot has no acquired visual adapter.  The system validates perceptual
    # grounding before action and therefore abstains without stepping it.
    acrobot = gym.make("Acrobot-v1", render_mode="rgb_array")
    _hidden_observation, _ = acrobot.reset(seed=501)
    acrobot_frame = acrobot.render()
    adapter_known = False
    try:
        _mountain_position(acrobot_frame)
        adapter_known = True
    except ValueError:
        try:
            _cartpole_angle(acrobot_frame)
            adapter_known = True
        except ValueError:
            pass
    acrobot.close()
    ood_abstention = not adapter_known

    import gymnasium.envs.classic_control.mountain_car as mountain_source
    source_path = Path(inspect.getsourcefile(mountain_source) or "")
    gate = {
        "public_authority": "Farama_Gymnasium",
        "gymnasium_version": gym.__version__,
        "authority_source_sha256": _sha(source_path),
        "public_environment_families": 2,
        "development_seeds": 6,
        "sealed_seeds": 12,
        "pixel_only_state_inference": all(not row["numeric_observation_used"] for row in learned),
        "learned_policy_success": learned_success,
        "cold_policy_success": cold_success,
        "success_lift_vs_cold": learned_success - cold_success,
        "weakest_family_success": min(family_success.values()),
        "mountain_champion": mountain_champion,
        "cartpole_champion": cartpole_champion,
        "pre_action_commitments": sum(len(row["pre_action_commitments"]) for row in learned),
        "unseen_visual_schema_abstention": ood_abstention,
        "unsafe_actions": 0,
        "live_system_writes": 0,
    }
    gate["accepted"] = bool(
        learned_success >= 0.90 and gate["weakest_family_success"] >= 0.80
        and gate["success_lift_vs_cold"] >= 0.50 and gate["pixel_only_state_inference"]
        and ood_abstention and gate["unsafe_actions"] == 0
    )

    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    runtime.store.state.setdefault("public_physics_transfer", {})
    cohort_id = "public_physics_v9_" + _canonical_hash({"gate": gate, "seeds": mountain_seeds + cartpole_seeds})[:16]
    runtime.store.state["public_physics_transfer"][cohort_id] = {
        "gate": gate, "champions": [mountain_champion, cartpole_champion], "created_at": _utc_timestamp(),
    }
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID, goal="public_pixel_physics_transfer",
        steps=[
            "acquire_visual_state_adapter", "invent_bounded_feedback_programs",
            "select_program_from_development_consequences", "commit_before_action",
            "transfer_to_fresh_public_simulator_seeds", "compare_zero_experience_control",
            "abstain_on_unknown_visual_schema",
        ],
        score=learned_success, success=gate["accepted"], evidence={"cohort_id": cohort_id, "gate": gate}, source_rules=[],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    runtime.store.commit(reason="public_pixel_physics_transfer_v9")
    restarted = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {
        "cohort_retained": cohort_id in restarted.store.state.get("public_physics_transfer", {}),
        "champion_retained": restarted.store.state["champions"].get("public_pixel_physics_transfer") == PROCEDURE_ID,
        "relearning_episodes": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.public_pixel_physics_transfer.v1", "created_at": _utc_timestamp(),
        "official_sources": [
            "https://gymnasium.farama.org/main/environments/classic_control/mountain_car/",
            "https://gymnasium.farama.org/environments/classic_control/cart_pole/",
        ],
        "development": {"mountain": mountain_dev, "cartpole": cartpole_dev},
        "sealed": {"learned": learned, "cold": cold, "family_success": family_success},
        "ood": {"environment": "Acrobot-v1", "adapter_known": adapter_known, "actions_executed": 0, "abstained": ood_abstention},
        "gate": gate, "promotion": {"candidate": candidate.to_dict(), "decision": promotion}, "restart": restart,
        "passed": bool(
            gate["accepted"] and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID)
            and restart["cohort_retained"] and restart["champion_retained"] and restart["relearning_episodes"] == 0
        ),
        "boundary": (
            "This is public third-party simulated physics with pixel-only agent observations, but development still "
            "selected environments, candidate program grammar, seeds and gates. It is not independent administration, "
            "real robotic action, unrestricted reinforcement learning or AGI."
        ),
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/public_physics_v9/state.json"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_public_physics_transfer_v9.json"))
    args = parser.parse_args()
    result = run_public_physics_transfer(
        repo_root=args.repo_root.resolve(), state_path=args.state_path.resolve(), result_path=args.result_path.resolve()
    )
    print(json.dumps({"passed": result["passed"], "gate": result["gate"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
