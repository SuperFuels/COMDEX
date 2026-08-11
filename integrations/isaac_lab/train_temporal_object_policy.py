#!/usr/bin/env python3
"""Train a hash-bound recurrent visual skill from verified Isaac authorities."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from backend.modules.hexcore.temporal_object_centric_embodied_policy import (
    SCHEMA, TemporalObjectPolicy, canonical_digest, file_sha256,
)


def verified_archive(receipt_path: Path, archive_path: Path):
    receipt = json.loads(receipt_path.read_text())
    audit = receipt.get("audit") or {}
    required = ("completed_without_failure", "student_privileged_fields_absent",
                "commit_before_act_verified", "teacher_removed_evaluation_required")
    if any(audit.get(key) is not True for key in required):
        raise ValueError("trajectory_authority_incomplete")
    if file_sha256(archive_path) != (receipt.get("private_trajectory") or {}).get("sha256"):
        raise ValueError("trajectory_archive_integrity_failure")
    successful = {int(item["episode"]) for item in receipt.get("outcomes", [])
                  if item.get("success") is True}
    if audit.get("dagger_teacher_labels_verified") is True:
        selected = {int(item["episode"]) for item in receipt.get("outcomes", [])}
    else:
        selected = successful
    with np.load(archive_path, allow_pickle=False) as raw:
        arrays = {key: raw[key] for key in ("rgb", "proprioception", "action", "episode", "step")}
    episodes = []
    for episode in sorted(selected):
        indices = np.flatnonzero(arrays["episode"] == episode)
        indices = indices[np.argsort(arrays["step"][indices])]
        if len(indices):
            episodes.append((arrays["rgb"][indices], arrays["proprioception"][indices],
                             arrays["action"][indices]))
    if not episodes:
        raise ValueError("no_verified_sequences")
    return receipt, episodes


def batches(episodes, *, batch_size: int, chunk: int, generator: np.random.Generator):
    order = generator.permutation(len(episodes))
    for offset in range(0, len(order), batch_size):
        chosen = [episodes[index] for index in order[offset:offset + batch_size]]
        if not chosen:
            continue
        length = min(chunk, max(len(item[0]) for item in chosen))
        rgb = np.zeros((len(chosen), length, 96, 128, 3), dtype=np.uint8)
        proprio = np.zeros((len(chosen), length, chosen[0][1].shape[-1]), dtype=np.float32)
        action = np.zeros((len(chosen), length, chosen[0][2].shape[-1]), dtype=np.float32)
        valid = np.zeros((len(chosen), length), dtype=bool)
        for row, item in enumerate(chosen):
            maximum = max(0, len(item[0]) - length)
            start = int(generator.integers(0, maximum + 1)) if maximum else 0
            available = min(length, len(item[0]) - start)
            rgb[row, :available] = item[0][start:start + available, ..., :3]
            proprio[row, :available] = item[1][start:start + available]
            action[row, :available] = item[2][start:start + available]
            valid[row, :available] = True
        yield rgb, proprio, action, valid


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority", action="append", required=True,
                        help="receipt.json=archive.npz; may be repeated")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--epochs", type=int, default=180)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--chunk", type=int, default=64)
    args = parser.parse_args()

    receipts, episodes = [], []
    for pair in args.authority:
        receipt, archive = pair.split("=", 1)
        evidence, sequences = verified_archive(Path(receipt), Path(archive))
        receipts.append(evidence); episodes.extend(sequences)
    all_actions = np.concatenate([item[2] for item in episodes], axis=0).astype(np.float32)
    all_proprio = np.concatenate([item[1] for item in episodes], axis=0).astype(np.float32)
    action_mean, action_scale = all_actions.mean(0), all_actions.std(0)
    action_scale[action_scale < 1e-4] = 1.0
    action_low, action_high = all_actions.min(0), all_actions.max(0)
    margin = np.maximum((action_high - action_low) * .01, 1e-3)
    proprio_low, proprio_high = all_proprio.min(0), all_proprio.max(0)
    proprio_margin = np.maximum((proprio_high - proprio_low) * .20, .05)

    torch.manual_seed(271828)
    np_generator = np.random.default_rng(271828)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = TemporalObjectPolicy(proprio_dim=all_proprio.shape[1],
                                 action_dim=all_actions.shape[1], hidden_dim=256).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, args.epochs))
    epoch_losses = []
    model.train()
    for epoch in range(args.epochs):
        losses = []
        # Multiple independent crops per episode make every epoch a new
        # temporal practice set instead of repeatedly replaying one slice.
        for _ in range(3):
            for rgb, proprio, action, valid in batches(
                    episodes, batch_size=args.batch_size, chunk=args.chunk, generator=np_generator):
                rgb_t = torch.from_numpy(rgb).to(device)
                proprio_t = torch.from_numpy(proprio).to(device)
                valid_t = torch.from_numpy(valid).to(device)
                target = (action - action_mean) / action_scale
                target_t = torch.from_numpy(target).to(device)
                proposal = model.forward_sequence(rgb_t, proprio_t, valid_t)
                mask = valid_t.unsqueeze(-1).expand_as(proposal)
                loss = F.smooth_l1_loss(proposal[mask], target_t[mask])
                # Consecutive teacher actions provide an executable temporal
                # consistency property without exposing privileged state.
                if proposal.shape[1] > 1:
                    adjacent = (valid_t[:, 1:] & valid_t[:, :-1]).unsqueeze(-1).expand_as(proposal[:, 1:])
                    delta_p = proposal[:, 1:] - proposal[:, :-1]
                    delta_t = target_t[:, 1:] - target_t[:, :-1]
                    loss = loss + .15 * F.smooth_l1_loss(delta_p[adjacent], delta_t[adjacent])
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
                optimizer.step()
                losses.append(float(loss.detach().cpu()))
        scheduler.step()
        epoch_losses.append(float(np.mean(losses)))

    weights = Path(args.weights); weights.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.cpu().eval().state_dict(), weights)
    manifest = {
        "schema_version": SCHEMA,
        "teacher_authority": "proposal_only_removed_at_inference",
        "weights_sha256": file_sha256(weights),
        "source_receipt_sha256": sorted(hashlib.sha256(
            json.dumps(item, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            for item in receipts),
        "verified_episode_count": len(episodes),
        "verified_transition_count": int(sum(len(item[0]) for item in episodes)),
        "proprio_dim": int(all_proprio.shape[1]), "action_dim": int(all_actions.shape[1]),
        "hidden_dim": 256,
        "action_mean": action_mean.tolist(), "action_scale": action_scale.tolist(),
        "action_low": (action_low - margin).tolist(), "action_high": (action_high + margin).tolist(),
        "proprio_low": (proprio_low - proprio_margin).tolist(),
        "proprio_high": (proprio_high + proprio_margin).tolist(),
        "training_epochs": args.epochs,
        "final_training_loss": epoch_losses[-1],
        "minimum_training_loss": min(epoch_losses),
        "parameter_count": int(sum(parameter.numel() for parameter in model.parameters())),
        "input_authority": "RGB plus bounded joint position/velocity only",
        "prospective_teacher_removed_execution_required": True,
        "claim_boundary": "Training fit is not manipulation competence; PhysX must authorize later.",
    }
    manifest["capsule_digest"] = canonical_digest(manifest)
    output = Path(args.manifest); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps({key: manifest[key] for key in
                      ("capsule_digest", "verified_episode_count", "verified_transition_count",
                       "parameter_count", "final_training_loss")}, sort_keys=True))


if __name__ == "__main__":
    main()
