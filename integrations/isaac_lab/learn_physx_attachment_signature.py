"""Learn a compact PhysX grasp signature from later object consequences."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


SCHEMA = "aion.physx_attachment_signature.v1"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build(source: Path, receipt_path: Path, output: Path) -> dict[str, Any]:
    receipt = json.loads(receipt_path.read_text())
    authority = receipt.get("private_trajectory") or {}
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    authority_kind = "original_private_trajectory"
    if authority.get("sha256") != source_digest:
        # The retained contact archive had RGB removed after collection.  Its
        # exact transformed digest was independently gated by the previously
        # promoted contact-transition capsule; verify that complete lineage
        # instead of pretending the original archive remained byte-identical.
        lineage_path = source.with_name("contact_transition_capsule_v1.json")
        lineage = json.loads(lineage_path.read_text())
        unsigned = {k: v for k, v in lineage.items() if k != "capsule_sha256"}
        valid_lineage = (
            lineage.get("capsule_sha256") == _digest(unsigned)
            and lineage.get("source_archive_sha256") == source_digest
            and lineage.get("gate", {}).get("passed")
        )
        if not valid_lineage:
            raise RuntimeError("attachment_source_authority_mismatch")
        authority_kind = "verified_rgb_stripped_contact_transition_capsule"
    with np.load(source, allow_pickle=False) as z:
        touch = np.asarray(z["fingertip_touch"], np.float32)
        width = np.asarray(z["proprioception"], np.float32)[:, 7:9].mean(1)
        height = np.asarray(z["object_height_post"], np.float32)
        episode = np.asarray(z["episode"], np.int32)
        step = np.asarray(z["step"], np.int32)
    candidates = []
    episodes = np.unique(episode)
    # A later 3 cm object rise is the attachment authority. It includes
    # near-lifts that acquired the object but failed the stricter 10 cm exam.
    truth = {int(e): float(height[episode == e].max() - np.median(height[episode == e][:3])) >= .03
             for e in episodes}
    split = max(4, int(len(episodes) * 2 / 3))
    development_episodes = {int(e) for e in episodes[:split]}
    sealed_episodes = {int(e) for e in episodes[split:]}
    for force_min in (5., 10., 15., 20., 25., 30.):
      for balance in (.35, .50, .65, .75, .85):
       for width_low in (.010, .015, .018, .020):
        for width_high in (.026, .028, .030, .032, .036):
         predicted = {int(e): False for e in episodes}
         for index in range(3, len(touch)):
            if episode[index - 3] != episode[index] or step[index] <= step[index - 1]:
                continue
            median = np.median(touch[index - 3:index + 1], axis=0)
            ratio = float(median.min() / max(float(median.max()), 1e-6))
            if (median.min() >= force_min and ratio >= balance
                    and width_low <= width[index] <= width_high):
                predicted[int(episode[index])] = True
         tp = sum(predicted[e] and truth[e] for e in development_episodes)
         fp = sum(predicted[e] and not truth[e] for e in development_episodes)
         fn = sum(not predicted[e] and truth[e] for e in development_episodes)
         precision = tp / max(tp + fp, 1)
         recall = tp / max(tp + fn, 1)
         f1 = 2 * precision * recall / max(precision + recall, 1e-9)
         candidates.append((f1, recall, precision, force_min, balance,
                            width_low, -width_high, predicted, tp, fp, fn))
    selected = max(candidates, key=lambda row: row[:7])
    f1, recall, precision, force_min, balance, width_low, negative_high, predicted, tp, fp, fn = selected
    sealed_tp = sum(predicted[e] and truth[e] for e in sealed_episodes)
    sealed_fp = sum(predicted[e] and not truth[e] for e in sealed_episodes)
    sealed_fn = sum(not predicted[e] and truth[e] for e in sealed_episodes)
    sealed_precision = sealed_tp / max(sealed_tp + sealed_fp, 1)
    sealed_recall = sealed_tp / max(sealed_tp + sealed_fn, 1)
    capsule = {
        "schema_version": SCHEMA,
        "history_steps": 4,
        "force_minimum": force_min,
        "force_maximum": 150.0,
        "minimum_force_balance_ratio": balance,
        "finger_width_minimum": width_low,
        "finger_width_maximum": -negative_high,
        "loss_debounce_steps": 2,
        "gate": {"passed": bool(recall == 1.0 and precision >= .80
                                  and sealed_recall == 1.0 and sealed_precision >= .80),
                 "attachment_episodes": int(sum(truth.values())),
                 "development": {"episodes": len(development_episodes),
                                 "true_positive_episodes": tp, "false_positive_episodes": fp,
                                 "false_negative_episodes": fn, "precision": precision,
                                 "recall": recall, "f1": f1},
                 "sealed": {"episodes": len(sealed_episodes),
                            "true_positive_episodes": sealed_tp,
                            "false_positive_episodes": sealed_fp,
                            "false_negative_episodes": sealed_fn,
                            "precision": sealed_precision, "recall": sealed_recall}},
        "authority": {"source_sha256": source_digest,
                      "lineage": authority_kind,
                      "later_consequence": "object_height_gain_at_least_0.03m",
                      "runtime_inputs": ["fingertip_touch_history", "finger_joint_width"],
                      "forbidden": ["object_pose", "reward", "teacher_action"]},
    }
    capsule["capsule_digest"] = _digest(capsule)
    if not capsule["gate"]["passed"]:
        raise RuntimeError("attachment_signature_heldout_gate_failed")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(capsule, indent=2, sort_keys=True))
    return capsule


class AttachmentSignature:
    def __init__(self, capsule: dict[str, Any]):
        unsigned = {k: v for k, v in capsule.items() if k != "capsule_digest"}
        if capsule.get("capsule_digest") != _digest(unsigned) or not capsule["gate"]["passed"]:
            raise RuntimeError("attachment_signature_capsule_rejected")
        self.c = capsule
        self.history: list[np.ndarray] = []
        self.loss_age = 0

    @classmethod
    def load(cls, path: Path) -> "AttachmentSignature":
        return cls(json.loads(path.read_text()))

    def reset(self) -> None:
        self.history = []
        self.loss_age = 0

    def update(self, touch: np.ndarray, finger_width: float) -> bool:
        touch = np.asarray(touch, np.float32)
        if touch.shape != (2,) or not np.all(np.isfinite(touch)) or np.any(touch < 0) or np.any(touch > 250):
            raise ValueError("attachment_signature_observation_rejected")
        self.history = (self.history + [touch])[-int(self.c["history_steps"]):]
        attached = False
        if len(self.history) == int(self.c["history_steps"]):
            median = np.median(np.stack(self.history), axis=0)
            ratio = float(median.min() / max(float(median.max()), 1e-6))
            attached = bool(
                median.min() >= self.c["force_minimum"]
                and median.max() <= self.c["force_maximum"]
                and ratio >= self.c["minimum_force_balance_ratio"]
                and self.c["finger_width_minimum"] <= finger_width <= self.c["finger_width_maximum"]
            )
        self.loss_age = 0 if attached else self.loss_age + 1
        return attached


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(build(
        root / "results/immutable/isaac_precision_franka/contact_transition_collection.npz",
        root / "results/immutable/isaac_precision_franka/contact_transition_collection_receipt.json",
        root / "results/immutable/isaac_precision_franka/physx_attachment_signature_v2.json",
    ), indent=2))
