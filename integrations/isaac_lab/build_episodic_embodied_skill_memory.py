#!/usr/bin/env python3
"""Compile verified Isaac episodes into a teacher-removed skill memory."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from backend.modules.hexcore.episodic_embodied_skill_memory import SCHEMA, digest, sha256, spatial_state


def authority(pair: str):
    receipt_name, archive_name = pair.split("=", 1)
    receipt_path, archive_path = Path(receipt_name), Path(archive_name)
    receipt = json.loads(receipt_path.read_text()); audit = receipt.get("audit") or {}
    if any(audit.get(key) is not True for key in
           ("completed_without_failure", "student_privileged_fields_absent",
            "commit_before_act_verified", "teacher_removed_evaluation_required")):
        raise ValueError("trajectory_authority_incomplete")
    if sha256(archive_path) != receipt["private_trajectory"]["sha256"]:
        raise ValueError("trajectory_archive_integrity_failure")
    selected = ({int(item["episode"]) for item in receipt["outcomes"]}
                if audit.get("dagger_teacher_labels_verified") is True else
                {int(item["episode"]) for item in receipt["outcomes"] if item.get("success") is True})
    with np.load(archive_path, allow_pickle=False) as raw:
        arrays = {key: raw[key] for key in ("rgb", "proprioception", "action", "episode", "step")}
    return receipt, arrays, selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority", action="append", required=True)
    parser.add_argument("--manifest", required=True); parser.add_argument("--archive", required=True)
    parser.add_argument("--neighbours", type=int, default=1)
    args = parser.parse_args()
    inputs = [authority(pair) for pair in args.authority]
    proprio = np.concatenate([item[1]["proprioception"] for item in inputs], axis=0).astype(np.float32)
    mean, scale = proprio.mean(0), proprio.std(0); scale[scale < 1e-5] = 1.0
    low, high = proprio.min(0), proprio.max(0); margin = np.maximum((high - low) * .2, .05)
    states, actions, steps, source_hashes = [], [], [], []
    for receipt, raw, selected in inputs:
        source_hashes.append(hashlib.sha256(json.dumps(receipt, sort_keys=True,
                                                       separators=(",", ":")).encode()).hexdigest())
        for episode in sorted(selected):
            indices = np.flatnonzero(raw["episode"] == episode)
            indices = indices[np.argsort(raw["step"][indices])]
            previous = None
            for index in indices:
                image = raw["rgb"][index, ..., :3]
                if previous is None: previous = image
                states.append(spatial_state(image, previous, raw["proprioception"][index],
                                            int(raw["step"][index]), proprio_mean=mean,
                                            proprio_scale=scale))
                actions.append(np.asarray(raw["action"][index], dtype=np.float32))
                steps.append(int(raw["step"][index]))
                previous = image
    state_matrix, action_matrix = np.vstack(states), np.vstack(actions)
    output = Path(args.archive); output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, states=state_matrix.astype(np.float16), actions=action_matrix,
                        steps=np.asarray(steps, dtype=np.int16))
    action_low, action_high = action_matrix.min(0), action_matrix.max(0)
    action_margin = np.maximum((action_high - action_low) * .01, 1e-3)
    # Sampled leave-neighbour distances set a permissive same-task envelope;
    # the outer execution contract remains the environment authority.
    # Consecutive verified states provide a conservative linear-time coverage
    # scale. Episode boundaries only enlarge this estimate and therefore cannot
    # create a false rejection of an otherwise familiar same-task reset.
    consecutive = np.linalg.norm(np.diff(state_matrix, axis=0), axis=1)
    radius = max(5.0, float(np.quantile(consecutive, .995) * 6.0))
    manifest = {
        "schema_version": SCHEMA, "archive_sha256": sha256(output),
        "source_receipt_sha256": sorted(source_hashes), "verified_transition_count": len(states),
        "proprio_mean": mean.tolist(), "proprio_scale": scale.tolist(),
        "proprio_low": (low - margin).tolist(), "proprio_high": (high + margin).tolist(),
        "action_low": (action_low - action_margin).tolist(),
        "action_high": (action_high + action_margin).tolist(),
        "neighbour_count": args.neighbours, "retrieval_temperature": .05,
        "phase_window": 1,
        "ood_radius": radius, "teacher_authority": "removed_at_inference",
        "input_authority": "two-frame RGB, bounded proprioception and public episode time",
        "prospective_execution_required": True,
    }
    manifest["capsule_digest"] = digest(manifest)
    path = Path(args.manifest); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps({"capsule_digest": manifest["capsule_digest"], "states": len(states),
                      "feature_dim": state_matrix.shape[1], "ood_radius": radius}, sort_keys=True))


if __name__ == "__main__": main()
