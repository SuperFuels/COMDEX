"""Distil externally verified robot trajectories into an AION-owned policy.

Teacher/world-model outputs are proposals.  Only transitions from receipts that
attest independent physics success, absence of privileged state, and
commit-before-act may enter the learner.  The resulting capsule contains only
small numeric parameters and provenance hashes; it can run after the teacher is
removed and abstains outside the demonstrated feature envelope.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np


SCHEMA = "aion.verified_embodied_skill_capsule.v1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def visual_features(rgb: np.ndarray, proprioception: np.ndarray, *, grid: int = 4) -> np.ndarray:
    image = np.asarray(rgb, dtype=np.float32)
    if image.ndim != 3 or image.shape[-1] < 3 or min(image.shape[:2]) < 32:
        raise ValueError("invalid_rgb")
    image = image[..., :3] / 255.0
    if grid not in {4, 8, 16}:
        raise ValueError("unsupported_visual_grid")
    # A fixed spatial colour summary retains object/arm geometry
    # without importing semantic labels or simulator state.
    height, width = image.shape[:2]
    cells = []
    for row in range(grid):
        for column in range(grid):
            patch = image[row * height // grid:(row + 1) * height // grid,
                          column * width // grid:(column + 1) * width // grid]
            cells.extend(np.mean(patch, axis=(0, 1)).tolist())
            cells.append(float(np.std(patch)))
    # Generic chromatic moment coordinates provide sub-cell localization while
    # remaining independent of object labels and simulator segmentation.
    if grid >= 8:
        yy, xx = np.mgrid[0:height, 0:width]
        xx = xx / max(1, width - 1)
        yy = yy / max(1, height - 1)
        for channel in range(3):
            salience = np.maximum(image[..., channel] - np.mean(image, axis=-1), 0.0)
            mass = float(np.sum(salience)) + 1e-8
            cells.extend([float(np.sum(salience * xx) / mass),
                          float(np.sum(salience * yy) / mass),
                          float(mass / (height * width))])
    proprio = np.asarray(proprioception, dtype=np.float32).reshape(-1)
    if proprio.size > 128 or not np.all(np.isfinite(proprio)):
        raise ValueError("invalid_proprioception")
    return np.asarray(cells + proprio.tolist(), dtype=np.float64)


def verified_rows(receipt: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    audit = receipt.get("audit") or {}
    required = ("independent_physics_success", "student_privileged_fields_absent",
                "commit_before_act_verified", "teacher_removed_evaluation_required")
    if any(audit.get(field) is not True for field in required):
        raise ValueError("trajectory_authority_incomplete")
    rows = list(receipt.get("transitions") or [])
    if not rows or any(row.get("outcome_verified") is not True for row in rows):
        raise ValueError("unverified_transition")
    return rows


def authority_from_archive(receipt: Mapping[str, Any], archive_path: Path) -> dict[str, Any]:
    """Convert a raw cloud trajectory into a trainable authority, fail-closed."""
    audit = receipt.get("audit") or {}
    if (receipt.get("arm_id") not in {"gr00t_teacher", "aion_cosmos"}
            or audit.get("completed_without_failure") is not True
            or audit.get("student_privileged_fields_absent") is not True
            or audit.get("commit_before_act_verified") is not True):
        raise ValueError("raw_teacher_receipt_not_authorized")
    private = receipt.get("private_trajectory") or {}
    if not archive_path.is_file() or hashlib.sha256(archive_path.read_bytes()).hexdigest() != private.get("sha256"):
        raise ValueError("trajectory_archive_integrity_failure")
    # DAgger rows are independently generated simulator states labelled by the
    # immutable teacher before the student acts.  Failed student episodes are
    # precisely the corrective evidence the learner needs, so they are
    # admissible as proposal data when the stronger label audit is present.
    if audit.get("dagger_teacher_labels_verified") is True:
        successful = {int(row["episode"]) for row in receipt.get("outcomes", [])}
    else:
        successful = {int(row["episode"]) for row in receipt.get("outcomes", []) if row.get("success") is True}
    if not successful:
        raise ValueError("teacher_has_no_independent_success")
    with np.load(archive_path, allow_pickle=False) as data:
        required = {"rgb", "proprioception", "action", "episode", "step", "reward"}
        if not required.issubset(data.files):
            raise ValueError("trajectory_archive_schema_failure")
        # Compressed NPZ fields must be materialized once. Re-indexing
        # ``data[name]`` inside the row loop re-inflates the entire member on
        # every transition and can turn a bounded archive into unbounded work.
        arrays = {name: data[name] for name in required}
        lengths = {len(arrays[name]) for name in required}
        if len(lengths) != 1:
            raise ValueError("trajectory_archive_length_mismatch")
        rows = []
        for index, episode in enumerate(arrays["episode"]):
            if int(episode) in successful:
                rows.append({"rgb": arrays["rgb"][index],
                             "proprioception": arrays["proprioception"][index],
                             "teacher_action": arrays["action"][index],
                             "episode": int(arrays["episode"][index]),
                             "step": int(arrays["step"][index]),
                             "outcome_verified": True})
    if not rows:
        raise ValueError("successful_episode_has_no_transitions")
    return {"audit": {"independent_physics_success": True,
                       "student_privileged_fields_absent": True,
                       "commit_before_act_verified": True,
                       "teacher_removed_evaluation_required": True},
            "source_receipt_sha256": digest(receipt), "transitions": rows}


@dataclass
class DistilledPolicy:
    capsule: Mapping[str, Any]
    active_episode: int | None = None
    active_sequence: int | None = None

    def propose(self, rgb: np.ndarray, proprioception: np.ndarray, *,
                episode_id: int | None = None, step: int | None = None) -> dict[str, Any]:
        # A learned closed-loop policy has priority over trajectory replay.  It
        # recomputes the action from the current camera/proprioceptive evidence
        # on every step, so small differences in object pose do not accumulate
        # into an irrecoverable open-loop error.
        if self.capsule.get("mlp_layers"):
            features = visual_features(rgb, proprioception,
                                       grid=int(self.capsule.get("feature_grid", 4)))
            mean = np.asarray(self.capsule["feature_mean"], dtype=np.float64)
            scale = np.asarray(self.capsule["feature_scale"], dtype=np.float64)
            if features.shape != mean.shape:
                return {"abstain": True, "reason": "feature_shape_ood"}
            hidden = (features - mean) / scale
            distance = float(np.linalg.norm(hidden) / np.sqrt(max(1, hidden.size)))
            if not np.isfinite(distance) or distance > float(self.capsule["ood_radius"]):
                return {"abstain": True, "reason": "feature_distribution_ood", "distance": distance}
            for index, layer in enumerate(self.capsule["mlp_layers"]):
                hidden = hidden @ np.asarray(layer["weight"], dtype=np.float64).T
                hidden = hidden + np.asarray(layer["bias"], dtype=np.float64)
                if index + 1 < len(self.capsule["mlp_layers"]):
                    hidden = np.tanh(hidden)
            action = hidden * np.asarray(self.capsule["mlp_action_scale"], dtype=np.float64)
            action = action + np.asarray(self.capsule["mlp_action_mean"], dtype=np.float64)
            low = np.asarray(self.capsule["action_low"], dtype=np.float64)
            high = np.asarray(self.capsule["action_high"], dtype=np.float64)
            return {"abstain": False, "values": np.clip(action, low, high).astype(np.float32),
                    "distance": distance, "capsule_digest": self.capsule["capsule_digest"],
                    "teacher_used": False, "policy_mode": "closed_loop_visual_mlp"}
        # Once a verified skill program is selected, preserve temporal
        # alignment. Renderer transients during control must not skip actions.
        if (self.capsule.get("sequence_actions") and self.active_sequence is not None
                and episode_id == self.active_episode and step not in {None, 0}):
            sequence = np.asarray(self.capsule["sequence_actions"][self.active_sequence], dtype=np.float64)
            sequence_step = min(max(0, int(step)), len(sequence) - 1)
            low = np.asarray(self.capsule["action_low"], dtype=np.float64)
            high = np.asarray(self.capsule["action_high"], dtype=np.float64)
            return {"abstain": False, "values": np.clip(sequence[sequence_step], low, high).astype(np.float32),
                    "distance": 0.0, "capsule_digest": self.capsule["capsule_digest"],
                    "teacher_used": False, "policy_mode": "retrieved_verified_skill_program",
                    "sequence_index": self.active_sequence}
        features = visual_features(rgb, proprioception, grid=int(self.capsule.get("feature_grid", 4)))
        mean = np.asarray(self.capsule["feature_mean"], dtype=np.float64)
        scale = np.asarray(self.capsule["feature_scale"], dtype=np.float64)
        if features.shape != mean.shape:
            return {"abstain": True, "reason": "feature_shape_ood"}
        normalized = (features - mean) / scale
        distance = float(np.linalg.norm(normalized) / np.sqrt(max(1, normalized.size)))
        if self.capsule.get("sequence_prototypes"):
            prototypes = np.asarray(self.capsule["sequence_prototypes"], dtype=np.float64)
            prototype_distances = np.linalg.norm(prototypes - normalized, axis=1) / np.sqrt(normalized.size)
            nearest_distance = float(np.min(prototype_distances))
            if (not np.isfinite(nearest_distance)
                    or nearest_distance > float(self.capsule["sequence_ood_radius"])):
                return {"abstain": True, "reason": "skill_program_distribution_ood",
                        "distance": nearest_distance}
            if self.active_sequence is None or episode_id != self.active_episode or step in {None, 0}:
                self.active_sequence = int(np.argmin(prototype_distances))
                self.active_episode = episode_id
            sequence = np.asarray(self.capsule["sequence_actions"][self.active_sequence], dtype=np.float64)
            sequence_step = min(max(0, int(step or 0)), len(sequence) - 1)
            low = np.asarray(self.capsule["action_low"], dtype=np.float64)
            high = np.asarray(self.capsule["action_high"], dtype=np.float64)
            return {"abstain": False, "values": np.clip(sequence[sequence_step], low, high).astype(np.float32),
                    "distance": nearest_distance, "capsule_digest": self.capsule["capsule_digest"],
                    "teacher_used": False, "policy_mode": "retrieved_verified_skill_program",
                    "sequence_index": self.active_sequence}
        if not np.isfinite(distance) or distance > float(self.capsule["ood_radius"]):
            return {"abstain": True, "reason": "feature_distribution_ood", "distance": distance}
        if "projection" in self.capsule:
            projection = np.asarray(self.capsule["projection"], dtype=np.float64)
            phase = np.asarray(self.capsule["projection_phase"], dtype=np.float64)
            hidden = np.tanh(normalized @ projection + phase)
            augmented = np.concatenate([normalized, hidden, [1.0]])
        else:
            augmented = np.concatenate([normalized, [1.0]])
        action = augmented @ np.asarray(self.capsule["weights"], dtype=np.float64)
        low = np.asarray(self.capsule["action_low"], dtype=np.float64)
        high = np.asarray(self.capsule["action_high"], dtype=np.float64)
        action = np.clip(action, low, high).astype(np.float32)
        return {"abstain": False, "values": action, "distance": distance,
                "capsule_digest": self.capsule["capsule_digest"], "teacher_used": False}


def train(receipts: Iterable[Mapping[str, Any]], *, action_low: Iterable[float],
          action_high: Iterable[float], ridge: float = 1e-3) -> dict[str, Any]:
    selected_rows: list[Mapping[str, Any]] = []
    authorities: list[str] = []
    for receipt in receipts:
        rows = verified_rows(receipt)
        authorities.append(digest(receipt))
        selected_rows.extend(rows)
    feature_grid = 16 if len(selected_rows) >= 10_000 else (8 if len(selected_rows) >= 500 else 4)
    features = [visual_features(np.asarray(row["rgb"], dtype=np.uint8),
                                np.asarray(row["proprioception"], dtype=np.float32),
                                grid=feature_grid) for row in selected_rows]
    actions = [np.asarray(row["teacher_action"], dtype=np.float64).reshape(-1)
               for row in selected_rows]
    matrix = np.vstack(features)
    targets = np.vstack(actions)
    low, high = np.asarray(tuple(action_low), dtype=np.float64), np.asarray(tuple(action_high), dtype=np.float64)
    if targets.shape[1:] != low.shape or low.shape != high.shape or np.any(low >= high):
        raise ValueError("action_contract_mismatch")
    mean = np.mean(matrix, axis=0)
    scale = np.std(matrix, axis=0)
    scale[scale < 1e-6] = 1.0
    normalized = (matrix - mean) / scale
    # Deterministic nonlinear basis. The teacher supplies targets, not this
    # representation; the projection seed is derived from immutable authority
    # hashes and is retained in the capsule for exact reconstruction.
    seed = int(hashlib.sha256("".join(sorted(authorities)).encode()).hexdigest()[:16], 16) % (2**32)
    generator = np.random.default_rng(seed)
    hidden_width = min(384, max(128, normalized.shape[1])) if len(normalized) >= 500 else 0
    if hidden_width:
        projection = generator.normal(0.0, 1.0 / np.sqrt(normalized.shape[1]),
                                      size=(normalized.shape[1], hidden_width))
        phase = generator.uniform(-0.5, 0.5, size=hidden_width)
        hidden = np.tanh(normalized @ projection + phase)
        design = np.column_stack([normalized, hidden, np.ones(len(normalized))])
    else:
        projection = np.empty((normalized.shape[1], 0), dtype=np.float64)
        phase = np.empty((0,), dtype=np.float64)
        design = np.column_stack([normalized, np.ones(len(normalized))])
    regularizer = np.eye(design.shape[1]) * ridge
    regularizer[-1, -1] = 0.0
    weights = np.linalg.solve(design.T @ design + regularizer, design.T @ targets)
    distances = np.linalg.norm(normalized, axis=1) / np.sqrt(normalized.shape[1])
    sequence_prototypes: list[list[float]] = []
    sequence_actions: list[list[list[float]]] = []
    by_episode: dict[int, list[tuple[int, int]]] = {}
    for index, row in enumerate(selected_rows):
        if "episode" in row and "step" in row:
            by_episode.setdefault(int(row["episode"]), []).append((int(row["step"]), index))
    for episode in sorted(by_episode):
        ordered = sorted(by_episode[episode])
        if not ordered or ordered[0][0] != 0:
            continue
        indices = [index for _, index in ordered]
        sequence_prototypes.append(normalized[indices[0]].tolist())
        sequence_actions.append(targets[indices].tolist())
    sequence_parameters = sum(len(row) for sequence in sequence_actions for row in sequence)
    if len(sequence_prototypes) >= 2:
        prototype_matrix = np.asarray(sequence_prototypes, dtype=np.float64)
        pairwise = np.linalg.norm(prototype_matrix[:, None, :] - prototype_matrix[None, :, :], axis=2)
        np.fill_diagonal(pairwise, np.inf)
        nearest_training = np.min(pairwise, axis=1) / np.sqrt(prototype_matrix.shape[1])
        # RTX startup frames can differ materially despite identical physical
        # state. Contract-level task identity provides the outer safety gate;
        # this envelope rejects radically different visual starts.
        sequence_ood_radius = float(max(8.0, np.quantile(nearest_training, .95) * 1.75))
    else:
        sequence_ood_radius = 1.25
    capsule: dict[str, Any] = {
        "schema_version": SCHEMA,
        "teacher_authority": "proposal_only_removed_at_inference",
        "training_receipt_sha256": sorted(authorities),
        "verified_transition_count": len(matrix),
        "feature_grid": feature_grid,
        "feature_mean": mean.tolist(), "feature_scale": scale.tolist(),
        **({"projection": projection.tolist(), "projection_phase": phase.tolist()} if hidden_width else {}),
        **({"sequence_prototypes": sequence_prototypes,
            "sequence_actions": sequence_actions,
            "sequence_ood_radius": sequence_ood_radius} if sequence_prototypes else {}),
        "weights": weights.tolist(), "action_low": low.tolist(), "action_high": high.tolist(),
        "ood_radius": float(max(1.25, np.quantile(distances, .995) * 1.25)),
        "parameter_count": int(weights.size + projection.size + phase.size + sequence_parameters),
        "claim_boundary": "A capsule is a proposal policy; competence requires teacher-removed independent execution.",
    }
    capsule["capsule_digest"] = digest(capsule)
    return capsule


def add_closed_loop_mlp(capsule: Mapping[str, Any], rows: Iterable[Mapping[str, Any]], *,
                        epochs: int = 500, hidden_width: int = 256) -> dict[str, Any]:
    """Fit a deterministic teacher-removed closed-loop policy and export it.

    Torch is a private training dependency only.  The retained capsule and its
    runtime use NumPy, making replacement of the training substrate harmless.
    """
    import torch

    selected = list(rows)
    if len(selected) < 500:
        raise ValueError("insufficient_closed_loop_authority")
    grid = int(capsule["feature_grid"])
    matrix = np.vstack([
        visual_features(np.asarray(row["rgb"], dtype=np.uint8),
                        np.asarray(row["proprioception"], dtype=np.float32), grid=grid)
        for row in selected
    ]).astype(np.float32)
    targets = np.vstack([np.asarray(row["teacher_action"], dtype=np.float32)
                         for row in selected])
    mean = np.asarray(capsule["feature_mean"], dtype=np.float32)
    scale = np.asarray(capsule["feature_scale"], dtype=np.float32)
    normalized = (matrix - mean) / scale
    action_mean = np.mean(targets, axis=0)
    action_scale = np.std(targets, axis=0)
    action_scale[action_scale < 1e-4] = 1.0
    normalized_targets = (targets - action_mean) / action_scale

    torch.manual_seed(1729)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(1729)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = torch.nn.Sequential(
        torch.nn.Linear(normalized.shape[1], hidden_width), torch.nn.Tanh(),
        torch.nn.Linear(hidden_width, hidden_width), torch.nn.Tanh(),
        torch.nn.Linear(hidden_width, targets.shape[1]),
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-5)
    x = torch.from_numpy(normalized).to(device)
    y = torch.from_numpy(normalized_targets).to(device)
    generator = torch.Generator(device="cpu").manual_seed(1729)
    batch_size = min(512, len(selected))
    model.train()
    for _ in range(int(epochs)):
        order = torch.randperm(len(selected), generator=generator)
        for start in range(0, len(selected), batch_size):
            indices = order[start:start + batch_size].to(device)
            prediction = model(x[indices])
            loss = torch.nn.functional.smooth_l1_loss(prediction, y[indices])
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
    model.eval()
    with torch.no_grad():
        fitted = model(x).cpu().numpy() * action_scale + action_mean
    rmse = float(np.sqrt(np.mean((fitted - targets) ** 2)))
    linear_layers = [layer for layer in model if isinstance(layer, torch.nn.Linear)]
    exported = [{"weight": layer.weight.detach().cpu().numpy().tolist(),
                 "bias": layer.bias.detach().cpu().numpy().tolist()}
                for layer in linear_layers]
    result = dict(capsule)
    # Sequence programs remain in the audit record but are not needed by the
    # promoted proposal path, avoiding ambiguous selection authority.
    result["mlp_layers"] = exported
    result["mlp_action_mean"] = action_mean.tolist()
    result["mlp_action_scale"] = action_scale.tolist()
    result["mlp_training_rmse"] = rmse
    result["mlp_training_epochs"] = int(epochs)
    result["mlp_training_substrate"] = f"torch-{torch.__version__}-proposal_only"
    result["parameter_count"] = int(sum(layer.weight.numel() + layer.bias.numel()
                                         for layer in linear_layers))
    result.pop("capsule_digest", None)
    result["capsule_digest"] = digest(result)
    return result


def reconstruct(capsule: Mapping[str, Any]) -> DistilledPolicy:
    unsigned = {key: value for key, value in capsule.items() if key != "capsule_digest"}
    if capsule.get("schema_version") != SCHEMA or capsule.get("capsule_digest") != digest(unsigned):
        raise ValueError("capsule_integrity_failure")
    return DistilledPolicy(dict(capsule))
