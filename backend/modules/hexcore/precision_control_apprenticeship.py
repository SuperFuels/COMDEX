"""Simulator-neutral precision-control apprenticeship under MuJoCo authority.

The retained capability is not a memorized trajectory.  It identifies an
unfamiliar body's action delay, actuator effectiveness and damping, predicts
movement consequences, brakes before overshoot and re-calibrates its action
scale from observed residuals.  The same controller operates one-dimensional
motion, planar motion and a five-axis abstract tool-centre-point/gripper body.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import mujoco
import numpy as np

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PROCEDURE_ID = "procedure_cross_body_precision_control_apprenticeship_v1"
DT = 0.02


@dataclass(frozen=True)
class PrecisionWorld:
    world_id: str
    dimensions: int
    gain: tuple[float, ...]
    damping: tuple[float, ...]
    delay: int
    target: tuple[float, ...]
    disturbance_step: int = 120
    disturbance: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        fields = (self.gain, self.damping, self.target)
        if any(len(value) != self.dimensions for value in fields):
            raise ValueError("precision_world_dimension_mismatch")
        if self.disturbance and len(self.disturbance) != self.dimensions:
            raise ValueError("precision_disturbance_dimension_mismatch")
        if not 1 <= self.dimensions <= 5 or not 0 <= self.delay <= 3:
            raise ValueError("precision_world_out_of_contract")


class PrecisionMotionAuthority:
    """Owns hidden dynamics and scores stop-at-target precision."""

    def __init__(self, spec: PrecisionWorld, *, steps: int = 260) -> None:
        self.__spec = spec
        self.__steps_limit = steps
        self.__model = mujoco.MjModel.from_xml_string(self._xml(spec))
        self.__data = mujoco.MjData(self.__model)
        self.__issued: list[np.ndarray] = []
        self.__commits: list[str] = []
        self.__step = 0
        self.__unsafe = False
        self.__errors: list[float] = []
        self.__speeds: list[float] = []
        self.__prediction_errors: list[float] = []
        self.__disturbance_applied = False
        self.reset()

    @staticmethod
    def _xml(spec: PrecisionWorld) -> str:
        bodies = []
        motors = []
        for index in range(spec.dimensions):
            low, high = (-1.5, 1.5)
            bodies.append(
                f'<body name="axis{index}" pos="0 {index * 0.16} 0.6">'
                f'<joint name="q{index}" type="slide" axis="1 0 0" '
                f'damping="{spec.damping[index]}" armature="0.12" '
                f'range="{low} {high}" limited="true"/>'
                f'<geom type="sphere" size=".035" mass="1" rgba=".15 .65 .95 1"/>'
                '</body>'
            )
            motors.append(
                f'<motor name="u{index}" joint="q{index}" gear="{spec.gain[index]}" '
                'ctrllimited="true" ctrlrange="-1 1"/>'
            )
        return f"""<mujoco model="precision_body">
  <option timestep="{DT}" gravity="0 0 0" integrator="RK4"/>
  <worldbody>
    {''.join(bodies)}
  </worldbody>
  <actuator>{''.join(motors)}</actuator>
</mujoco>"""

    @property
    def dimensions(self) -> int:
        return self.__spec.dimensions

    def reset(self) -> Mapping[str, np.ndarray | int]:
        mujoco.mj_resetData(self.__model, self.__data)
        self.__data.qpos[:] = 0.0
        self.__data.qvel[:] = 0.0
        mujoco.mj_forward(self.__model, self.__data)
        self.__issued = []
        self.__commits = []
        self.__step = 0
        self.__unsafe = False
        self.__errors = []
        self.__speeds = []
        self.__prediction_errors = []
        self.__disturbance_applied = False
        return self.observe()

    def observe(self) -> Mapping[str, np.ndarray | int]:
        return {
            "position": np.asarray(self.__data.qpos).copy(),
            "velocity": np.asarray(self.__data.qvel).copy(),
            "target": np.asarray(self.__spec.target, dtype=float).copy(),
            "step": self.__step,
        }

    def commit(self, action: np.ndarray, predicted_position: np.ndarray) -> str:
        action = np.asarray(action, dtype=float)
        predicted_position = np.asarray(predicted_position, dtype=float)
        if action.shape != (self.dimensions,) or predicted_position.shape != action.shape:
            raise ValueError("precision_commit_shape_rejected")
        if not np.all(np.isfinite(action)) or not np.all(np.isfinite(predicted_position)):
            raise ValueError("precision_non_finite_commit_rejected")
        if np.any(np.abs(action) > 1.0):
            raise ValueError("precision_action_range_rejected")
        record = {
            "step": self.__step,
            "action": np.round(action, 9).tolist(),
            "predicted_position": np.round(predicted_position, 9).tolist(),
        }
        value = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
        self.__commits.append(value)
        return value

    def step(self, action: np.ndarray, predicted_position: np.ndarray) -> Mapping[str, Any]:
        action = np.asarray(action, dtype=float)
        if len(self.__commits) != self.__step + 1:
            raise RuntimeError("precision_commit_before_act_required")
        self.__issued.append(action.copy())
        applied_index = len(self.__issued) - 1 - self.__spec.delay
        applied = self.__issued[applied_index] if applied_index >= 0 else np.zeros_like(action)
        self.__data.ctrl[:] = applied
        mujoco.mj_step(self.__model, self.__data)
        self.__step += 1
        if self.__step == self.__spec.disturbance_step and self.__spec.disturbance:
            self.__data.qvel[:] += np.asarray(self.__spec.disturbance, dtype=float)
            mujoco.mj_forward(self.__model, self.__data)
            self.__disturbance_applied = True
        observation = self.observe()
        position = np.asarray(observation["position"])
        velocity = np.asarray(observation["velocity"])
        error = float(np.max(np.abs(position - np.asarray(self.__spec.target))))
        speed = float(np.max(np.abs(velocity)))
        self.__errors.append(error)
        self.__speeds.append(speed)
        self.__prediction_errors.append(float(np.max(np.abs(position - predicted_position))))
        if np.any(np.abs(position[: min(4, self.dimensions)]) > 1.48):
            self.__unsafe = True
        return {"observation": observation, "terminal": self.__step >= self.__steps_limit}

    def score(self) -> Mapping[str, Any]:
        observation = self.observe()
        position = np.asarray(observation["position"])
        velocity = np.asarray(observation["velocity"])
        final_error = float(np.max(np.abs(position - np.asarray(self.__spec.target))))
        final_speed = float(np.max(np.abs(velocity)))
        settled = [
            index
            for index in range(max(0, len(self.__errors) - 80), len(self.__errors) - 9)
            if max(self.__errors[index : index + 10]) <= 0.015
            and max(self.__speeds[index : index + 10]) <= 0.035
        ]
        post_disturbance = self.__errors[self.__spec.disturbance_step :] if self.__disturbance_applied else []
        recovered = (
            not self.__disturbance_applied
            or any(value <= 0.025 for value in post_disturbance[10:])
        )
        return {
            "final_error": final_error,
            "final_speed": final_speed,
            "settled": bool(settled),
            "settle_step": settled[0] if settled else None,
            "disturbance_recovered": bool(recovered),
            "mean_prediction_error": float(np.mean(self.__prediction_errors)),
            "safe": not self.__unsafe,
            "commitments": len(self.__commits),
            "success": bool(
                final_error <= 0.015
                and final_speed <= 0.035
                and recovered
                and not self.__unsafe
            ),
        }


@dataclass
class IdentifiedMotorModel:
    delay: int
    actuation: np.ndarray
    damping: np.ndarray
    residual: float
    condition_number: float
    minimum_authority: float
    acceleration_bias: np.ndarray | None = None
    relative_residual: float = 0.0
    position_effects: np.ndarray | None = None

    def bias_at(self, position: np.ndarray) -> np.ndarray:
        base = np.zeros_like(position) if self.acceleration_bias is None else self.acceleration_bias
        if self.position_effects is None:
            return base
        features = np.concatenate((np.sin(position), np.cos(position)))
        return base + self.position_effects @ features

    @property
    def reliable(self) -> bool:
        return bool(
            np.isfinite(self.residual)
            and (self.residual <= 1.0 or self.relative_residual <= 0.65)
            and np.isfinite(self.condition_number)
            and self.condition_number <= 100.0
            and self.minimum_authority >= 0.5
        )


class PredictivePrecisionController:
    """Identifies hidden motion response and uses uncertainty-aware braking."""

    def identify(self, authority: PrecisionMotionAuthority) -> IdentifiedMotorModel:
        observation = authority.reset()
        dimension = authority.dimensions
        issued: list[np.ndarray] = []
        positions = [np.asarray(observation["position"], dtype=float)]
        velocities = [np.asarray(observation["velocity"], dtype=float)]
        rng = np.random.default_rng(20260803 + dimension)
        for step in range(96):
            # Piecewise-constant, balanced probes make delay identifiable while
            # retaining the body inside a small safe neighborhood.
            block = step // 4
            visit = block // dimension
            sign = 1.0 if visit % 2 == 0 else -1.0
            action = np.zeros(dimension, dtype=float)
            action[block % dimension] = sign * float(rng.uniform(0.25, 0.55))
            position = positions[-1]
            predicted = position + velocities[-1] * DT
            authority.commit(action, predicted)
            result = authority.step(action, predicted)
            issued.append(action)
            positions.append(np.asarray(result["observation"]["position"], dtype=float))
            velocities.append(np.asarray(result["observation"]["velocity"], dtype=float))

        actions = np.asarray(issued)
        velocity = np.asarray(velocities)
        acceleration = (velocity[1:] - velocity[:-1]) / DT
        best: tuple[float, int, np.ndarray, np.ndarray, np.ndarray, float, np.ndarray] | None = None
        for delay in range(4):
            rows = np.arange(delay, len(actions))
            applied = actions[rows - delay]
            prior_velocity = velocity[rows]
            # The constant term is negligible in calibration lanes but becomes
            # essential when the retained method transfers to gravity-loaded
            # articulated bodies.
            position_features = np.column_stack((np.sin(np.asarray(positions)[rows]),
                                                 np.cos(np.asarray(positions)[rows])))
            design = np.column_stack((applied, prior_velocity, position_features,
                                      np.ones(len(rows))))
            coefficients, *_ = np.linalg.lstsq(design, acceleration[rows], rcond=None)
            actuation = coefficients[:dimension].T
            damping = -coefficients[dimension:2 * dimension].T
            position_effects = coefficients[2 * dimension:4 * dimension].T
            bias = coefficients[-1]
            prediction = design @ coefficients
            residual = float(np.sqrt(np.mean(np.square(prediction - acceleration[rows]))))
            scale = float(np.sqrt(np.mean(np.square(acceleration[rows]))))
            relative_residual = residual / max(scale, 1e-12)
            candidate = (residual, delay, actuation, damping, bias,
                         relative_residual, position_effects)
            if best is None or candidate[0] < best[0]:
                best = candidate
        assert best is not None
        singular_values = np.linalg.svd(best[2], compute_uv=False)
        minimum_authority = float(np.min(singular_values))
        condition_number = float(np.max(singular_values) / max(minimum_authority, 1e-12))
        return IdentifiedMotorModel(
            best[1], best[2], best[3], best[0], condition_number, minimum_authority,
            np.asarray(best[4], dtype=float), best[5], np.asarray(best[6], dtype=float),
        )

    @staticmethod
    def _predict_to_effect(
        position: np.ndarray,
        velocity: np.ndarray,
        issued: list[np.ndarray],
        model: IdentifiedMotorModel,
    ) -> tuple[np.ndarray, np.ndarray]:
        predicted_position = position.copy()
        predicted_velocity = velocity.copy()
        now = len(issued)
        for offset in range(model.delay):
            index = now - model.delay + offset
            applied = issued[index] if index >= 0 else np.zeros_like(position)
            bias = model.bias_at(predicted_position)
            acceleration = model.actuation @ applied - model.damping @ predicted_velocity + bias
            predicted_position = predicted_position + predicted_velocity * DT + 0.5 * acceleration * DT**2
            predicted_velocity = predicted_velocity + acceleration * DT
        return predicted_position, predicted_velocity

    def control(
        self, authority: PrecisionMotionAuthority, model: IdentifiedMotorModel, *, steps: int = 260
    ) -> Mapping[str, Any]:
        if not model.reliable:
            raise RuntimeError("precision_model_unreliable_abstain")
        observation = authority.reset()
        issued: list[np.ndarray] = []
        uncertainty_scale = float(np.clip(1.0 / (1.0 + model.residual), 0.35, 1.0))
        for _ in range(steps):
            position = np.asarray(observation["position"], dtype=float)
            velocity = np.asarray(observation["velocity"], dtype=float)
            target = np.asarray(observation["target"], dtype=float)
            future_position, future_velocity = self._predict_to_effect(position, velocity, issued, model)
            error = target - future_position
            # Critical damping with progressively smaller authority near the
            # target implements the learned "approach, brake, nudge" behavior.
            kp = 18.0
            kd = 2.0 * np.sqrt(kp)
            desired_acceleration = kp * error - kd * future_velocity
            action = np.linalg.pinv(model.actuation) @ (
                desired_acceleration + model.damping @ future_velocity
                - model.bias_at(future_position)
            )
            proximity = np.clip(np.max(np.abs(error)) / 0.12, 0.18, 1.0)
            limit = uncertainty_scale * proximity
            action = np.clip(action, -limit, limit)
            predicted_acceleration = (model.actuation @ action - model.damping @ velocity
                                      + model.bias_at(position))
            predicted_next = position + velocity * DT + 0.5 * predicted_acceleration * DT**2
            authority.commit(action, predicted_next)
            result = authority.step(action, predicted_next)
            issued.append(action.copy())
            observation = result["observation"]
        return {**authority.score(), "identified_delay": model.delay,
                "identified_actuation_matrix": model.actuation.tolist(),
                "identified_damping_matrix": model.damping.tolist(),
                "identification_residual": model.residual,
                "identification_relative_residual": model.relative_residual,
                "identification_condition_number": model.condition_number,
                "minimum_identified_authority": model.minimum_authority}


class ColdPrecisionController:
    """Matched controller with one fixed body assumption and no identification."""

    def control(self, authority: PrecisionMotionAuthority, *, steps: int = 260) -> Mapping[str, Any]:
        observation = authority.reset()
        dimension = authority.dimensions
        for _ in range(steps):
            position = np.asarray(observation["position"], dtype=float)
            velocity = np.asarray(observation["velocity"], dtype=float)
            target = np.asarray(observation["target"], dtype=float)
            action = np.clip((10.0 * (target - position) - 2.0 * velocity) / 12.0, -1.0, 1.0)
            predicted = position + velocity * DT
            authority.commit(action, predicted)
            observation = authority.step(action, predicted)["observation"]
        return authority.score()


DEVELOPMENT_WORLDS = (
    PrecisionWorld("dev_line", 1, (12.0,), (0.20,), 0, (0.72,), disturbance=(0.55,)),
    PrecisionWorld("dev_plane", 2, (9.0, 15.0), (0.12, 0.32), 1, (-0.55, 0.78), disturbance=(0.45, -0.35)),
)

SEALED_WORLDS = (
    PrecisionWorld("sealed_line_delay", 1, (7.0,), (0.55,), 2, (-0.83,), disturbance=(0.70,)),
    PrecisionWorld("sealed_plane_fast", 2, (18.0, 6.5), (0.08, 0.42), 1, (0.91, -0.68), disturbance=(-0.55, 0.60)),
    PrecisionWorld("sealed_xyz", 3, (8.0, 13.0, 5.5), (0.35, 0.14, 0.48), 2, (0.62, -0.73, 0.81), disturbance=(0.35, -0.40, 0.55)),
    PrecisionWorld("sealed_four_axis", 4, (15.0, 7.5, 11.0, 5.0), (0.10, 0.40, 0.22, 0.60), 3, (-0.70, 0.66, 0.48, 1.15), disturbance=(0.40, -0.45, 0.30, -0.60)),
    PrecisionWorld("sealed_five_axis", 5, (6.5, 17.0, 9.0, 7.0, 14.0), (0.50, 0.09, 0.30, 0.45, 0.18), 2, (0.58, -0.62, 0.72, -1.05, 0.34), disturbance=(-0.35, 0.42, -0.38, 0.50, 0.30)),
    PrecisionWorld("sealed_five_axis_slow", 5, (5.0, 6.0, 7.0, 4.5, 8.0), (0.65, 0.55, 0.45, 0.70, 0.40), 3, (-0.74, 0.52, -0.56, 0.88, 0.71), disturbance=(0.50, -0.40, 0.45, -0.55, -0.30)),
)


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True))
    json.loads(temporary.read_text())
    os.replace(temporary, path)


def _authority(_: str) -> dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "source": "precision_mujoco_private_cau",
        "S": 1.0,
        "H": 0.0,
    }


def run(repo_root: Path, result_path: Path | None = None,
        state_path: Path | None = None) -> dict[str, Any]:
    result_path = result_path or repo_root / "results/hexcore_precision_control_apprenticeship.json"
    state_path = state_path or repo_root / "backend/modules/hexcore/data/precision_control/state.json"
    learned = PredictivePrecisionController()
    development = []
    for spec in DEVELOPMENT_WORLDS:
        authority = PrecisionMotionAuthority(spec)
        model = learned.identify(authority)
        development.append({"world_id": spec.world_id, **learned.control(authority, model)})
    sealed = []
    cold = []
    for spec in SEALED_WORLDS:
        authority = PrecisionMotionAuthority(spec)
        model = learned.identify(authority)
        sealed.append({"world_id": spec.world_id, **learned.control(authority, model)})
        cold.append({"world_id": spec.world_id, **ColdPrecisionController().control(PrecisionMotionAuthority(spec))})
    malicious = []
    authority = PrecisionMotionAuthority(DEVELOPMENT_WORLDS[0])
    for name, action in (
        ("nan", np.asarray([np.nan])),
        ("out_of_range", np.asarray([1.2])),
        ("wrong_shape", np.asarray([0.1, 0.2])),
    ):
        rejected = False
        try:
            authority.commit(action, np.zeros_like(action))
        except ValueError:
            rejected = True
        malicious.append({"case": name, "rejected": rejected})
    weak_authority = PrecisionMotionAuthority(
        PrecisionWorld("ood_near_uncontrollable", 1, (0.01,), (0.4,), 1, (0.8,))
    )
    weak_model = learned.identify(weak_authority)
    ood_abstained = False
    try:
        learned.control(weak_authority, weak_model)
    except RuntimeError as exc:
        ood_abstained = str(exc) == "precision_model_unreliable_abstain"
    learned_success = sum(bool(row["success"]) for row in sealed)
    cold_success = sum(bool(row["success"]) for row in cold)
    mean_final_error = float(np.mean([row["final_error"] for row in sealed]))
    mean_cold_final_error = float(np.mean([row["final_error"] for row in cold]))
    precision_improvement_factor = mean_cold_final_error / max(mean_final_error, 1e-12)
    delay_accuracy = float(np.mean([
        int(row["identified_delay"] == spec.delay)
        for row, spec in zip(sealed, SEALED_WORLDS, strict=True)
    ]))
    gate_passed = bool(
        learned_success == len(sealed)
        and learned_success > cold_success
        and all(row["disturbance_recovered"] for row in sealed)
        and all(row["safe"] for row in sealed)
        and all(row["rejected"] for row in malicious)
        and ood_abstained
    )
    retained_method = {
        "name": "identify_predict_brake_micro_correct",
        "components": [
            "delay identification",
            "multivariate actuator and damping identification",
            "forward movement prediction",
            "uncertainty-scaled action authority",
            "predictive braking",
            "closed-loop micro-correction",
        ],
        "memorized_trajectories": 0,
        "body_specific_parameters_retained": 0,
    }
    learning = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_authority
    )
    cohort_id = "precision_control_" + _canonical_hash({
        "sealed": sealed, "cold": cold, "procedure": PROCEDURE_ID
    })[:16]
    learning.store.state.setdefault("precision_control_methods", {})[cohort_id] = {
        "method": retained_method,
        "gate": {"learned_success": learned_success, "cold_success": cold_success},
        "created_at": _utc_timestamp(),
    }
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="cross_dimensional_precision_control",
        steps=retained_method["components"],
        score=float(learned_success / max(1, len(sealed))),
        success=gate_passed,
        evidence={"cohort_id": cohort_id, "sealed_success": learned_success,
                  "cold_success": cold_success},
    )
    promotion = learning.skills.promote(candidate)
    learning.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=gate_passed,
        score=candidate.score, evidence=candidate.evidence,
    )
    learning.store.commit(reason="cross_dimensional_precision_control_apprenticeship_v1")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_authority
    )
    restart = {
        "cohort_retained": cohort_id in restarted.store.state.get("precision_control_methods", {}),
        "champion_retained": restarted.store.state.get("champions", {}).get(
            "cross_dimensional_precision_control"
        ) == PROCEDURE_ID,
    }
    passed = bool(gate_passed and all(restart.values()) and (
        promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID
    ))
    result = {
        "schema_version": "aion.precision_control_apprenticeship.v1",
        "procedure_id": PROCEDURE_ID,
        "created_at": _utc_timestamp(),
        "status": "PROMOTED" if passed else "REJECTED",
        "passed": passed,
        "development": development,
        "sealed": sealed,
        "cold": cold,
        "gates": {
            "sealed_success": learned_success,
            "sealed_total": len(sealed),
            "weakest_family_success": min(int(bool(row["success"])) for row in sealed),
            "cold_success": cold_success,
            "mean_final_error": mean_final_error,
            "mean_cold_final_error": mean_cold_final_error,
            "precision_improvement_factor_vs_cold": precision_improvement_factor,
            "hidden_delay_identification_accuracy": delay_accuracy,
            "pre_action_commitments": sum(int(row["commitments"]) for row in sealed),
            "all_disturbances_recovered": all(bool(row["disturbance_recovered"]) for row in sealed),
            "all_safe": all(bool(row["safe"]) for row in sealed),
            "malicious_rejected": sum(row["rejected"] for row in malicious),
            "ood_uncontrollable_abstention": ood_abstained,
        },
        "promotion_authorized": passed,
        "promotion": promotion,
        "restart": restart,
        "malicious": malicious,
        "retained_method": retained_method,
        "prediction_engine_integration": {
            "executive_prediction_engine_role": "mission feasibility and cognitive forecast",
            "precision_forward_model_role": "millisecond numerical movement consequences",
            "authority_boundary": "physical outcomes remain MuJoCo-owned",
        },
        "claim_boundary": "Cross-dimensional stop-at-target precision under local MuJoCo calibration lanes; not yet articulated-arm contact manipulation, locomotion or Isaac transfer.",
    }
    _atomic_json(result_path, result)
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(root), indent=2, sort_keys=True))
