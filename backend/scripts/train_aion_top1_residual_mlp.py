#!/usr/bin/env python3
"""Train a compact nonlinear top-1 residual cartridge with family-held-out selection."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from torch import nn


WIDTH = 2880
LAYERS = 36
EXPERTS = 128
BINS = 96


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def signed_bins(values: np.ndarray, seed: int) -> np.ndarray:
    """Cheap fixed structured projection: 2880 coordinates -> 96 signed bins."""
    rng = np.random.default_rng(seed)
    signs = rng.choice(np.asarray([-1.0, 1.0], dtype=np.float32), WIDTH)
    return (values * signs).reshape(len(values), BINS, WIDTH // BINS).sum(2) / np.sqrt(WIDTH // BINS)


def features(arrays: dict, rows: list[dict], feature_mode: str = "signed_bins") -> np.ndarray:
    if feature_mode == "full":
        projected = [np.asarray(arrays[name], dtype=np.float32)
                     for name in ("ffn", "router", "top1")]
    else:
        projected = [
            signed_bins(np.asarray(arrays[name], dtype=np.float32), seed)
            for name, seed in (("ffn", 1103), ("router", 2203), ("top1", 3301))
        ]
    route = np.zeros((len(rows), LAYERS * EXPERTS), dtype=np.float32)
    layer = np.zeros((len(rows), LAYERS), dtype=np.float32)
    gate_features = np.zeros((len(rows), 6), dtype=np.float32)
    for row_index, row in enumerate(rows):
        layer_id = int(row["layer"])
        layer[row_index, layer_id] = 1.0
        gates = np.asarray(row["gates"], dtype=np.float32)
        for expert, gate in zip(row["route"], gates):
            route[row_index, layer_id * EXPERTS + int(expert)] += float(gate)
        gate_features[row_index, :4] = gates[:4]
        gate_features[row_index, 4] = float(gates[1:].sum())
        gate_features[row_index, 5] = float(-np.sum(gates * np.log(np.maximum(gates, 1e-30))))
    return np.concatenate([*projected, route, layer, gate_features], axis=1)


class ResidualMLP(nn.Module):
    def __init__(self, input_width: int, hidden: int) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_width, hidden), nn.GELU(),
            nn.Linear(hidden, hidden), nn.GELU(),
            nn.Linear(hidden, WIDTH),
        )

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.network(value)


def train_model(x: np.ndarray, y: np.ndarray, indices: np.ndarray, hidden: int,
                weight_decay: float, epochs: int, seed: int,
                device: torch.device) -> tuple[ResidualMLP, np.ndarray, np.ndarray]:
    torch.manual_seed(seed)
    mean = x[indices].mean(0)
    scale = x[indices].std(0)
    scale[scale < 1e-5] = 1.0
    xt = torch.from_numpy(((x[indices] - mean) / scale).astype(np.float32)).to(device)
    yt = torch.from_numpy(y[indices].astype(np.float32)).to(device)
    norms = torch.linalg.vector_norm(yt, dim=1).clamp_min(1e-6)
    model = ResidualMLP(x.shape[1], hidden).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=weight_decay)
    for _ in range(epochs):
        optimizer.zero_grad(set_to_none=True)
        prediction = model(xt)
        loss = torch.mean(torch.sum((prediction - yt) ** 2, dim=1) / (norms ** 2))
        loss.backward()
        optimizer.step()
    return model.cpu(), mean.astype(np.float32), scale.astype(np.float32)


def errors(model: ResidualMLP, mean: np.ndarray, scale: np.ndarray,
           x: np.ndarray, y: np.ndarray, layer_output: np.ndarray,
           indices: np.ndarray) -> np.ndarray:
    with torch.no_grad():
        prediction = model(torch.from_numpy(((x[indices] - mean) / scale).astype(np.float32))).numpy()
    return np.linalg.norm(prediction - y[indices], axis=1) / np.maximum(
        np.linalg.norm(layer_output[indices], axis=1), 1e-30,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--cartridge", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=250)
    parser.add_argument("--feature-mode", choices=("signed_bins", "full"),
                        default="signed_bins")
    args = parser.parse_args()
    if args.cartridge.exists() or args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    authorization = json.loads(args.authorization.read_text())
    if authorization.get("authorized") is not True:
        raise SystemExit("explicit residual training authorization is absent")
    manifest = json.loads(args.dataset_manifest.read_text())
    if manifest.get("status") != "READY_FOR_AUTHORIZED_RESIDUAL_TRAINING":
        raise SystemExit("dataset is not authorized-training ready")
    dataset_path = Path(manifest["dataset_path"])
    if digest(dataset_path) != manifest["dataset_sha256"]:
        raise SystemExit("dataset hash mismatch")
    arrays = dict(np.load(dataset_path))
    rows = manifest["rows"]
    x = features(arrays, rows, args.feature_mode)
    y = np.asarray(arrays["omitted"], dtype=np.float32)
    layer_output = (np.asarray(arrays["ffn"], dtype=np.float32) +
                    np.asarray(arrays["full"], dtype=np.float32))
    families = sorted({row["family_id"] for row in rows if row["split"] == "train"})
    if len(families) < 2:
        raise SystemExit("family-held-out selection requires at least two training families")
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    candidates = ([(128, 1e-4), (256, 1e-4), (256, 1e-3), (512, 1e-3)]
                  if args.feature_mode == "full" else
                  [(64, 1e-4), (128, 1e-4), (128, 1e-3), (256, 1e-3)])
    selection = []
    for hidden, decay in candidates:
        fold_errors = []
        for fold, family in enumerate(families):
            train = np.asarray([i for i, row in enumerate(rows)
                                if row["split"] == "train" and row["family_id"] != family])
            held = np.asarray([i for i, row in enumerate(rows) if row["family_id"] == family])
            model, mean, scale = train_model(
                x, y, train, hidden, decay, args.epochs, 9100 + fold, device,
            )
            fold_errors.extend(errors(model, mean, scale, x, y, layer_output, held).tolist())
        selection.append({
            "hidden": hidden, "weight_decay": decay,
            "family_held_out_output_relative_l2_p50": float(np.median(fold_errors)),
            "family_held_out_output_relative_l2_p95": float(np.percentile(fold_errors, 95)),
        })
    selected = min(selection, key=lambda item: item["family_held_out_output_relative_l2_p95"])
    train = np.asarray([i for i, row in enumerate(rows) if row["split"] == "train"])
    model, mean, scale = train_model(
        x, y, train, int(selected["hidden"]), float(selected["weight_decay"]),
        args.epochs, 9200, device,
    )
    evaluations = {}
    for split in ("calibration", "numerical_holdout", "semantic_holdout"):
        indices = np.asarray([i for i, row in enumerate(rows) if row["split"] == split])
        value = errors(model, mean, scale, x, y, layer_output, indices)
        evaluations[split] = {
            "rows": len(indices), "output_relative_l2_p50": float(np.median(value)),
            "output_relative_l2_p95": float(np.percentile(value, 95)),
            "output_relative_l2_max": float(np.max(value)),
        }
    buffer = io.BytesIO()
    torch.save({"state_dict": model.state_dict(), "feature_mean": mean,
                "feature_scale": scale, "selected": selected}, buffer)
    payload = buffer.getvalue()
    args.cartridge.parent.mkdir(parents=True, exist_ok=True)
    args.cartridge.write_bytes(payload)
    sample = torch.from_numpy(((x[train[:1]] - mean) / scale).astype(np.float32))
    timings = []
    with torch.no_grad():
        for _ in range(100):
            started = time.perf_counter(); model(sample); timings.append((time.perf_counter() - started) * 1000)
    holdout_p95 = max(value["output_relative_l2_p95"] for value in evaluations.values())
    status = "READY_FOR_FROZEN_DEVELOPMENT" if holdout_p95 <= 0.02 else "STOP_NONLINEAR_RESIDUAL"
    report = {
        "schema": "aion.gptoss-120b-top1-residual-mlp-gate.v1",
        "status": status, "created_at": datetime.now(timezone.utc).isoformat(),
        "quality_track": True, "exact_fallback_required": True,
        "training_families": families, "family_held_out_selection": selection,
        "retained_experts": manifest.get("retained_experts", 1),
        "feature_mode": args.feature_mode,
        "selected": selected, "evaluations": evaluations,
        "cartridge_path": str(args.cartridge.resolve()),
        "cartridge_bytes": len(payload), "cartridge_sha256": digest(args.cartridge),
        "calculation_ms_p50": float(np.median(timings[10:])),
        "calculation_ms_p95": float(np.percentile(timings[10:], 95)),
        "dataset_manifest_canonical_sha256": manifest["canonical_sha256"],
        "authorization_sha256": digest(args.authorization),
        "frozen_evaluation_splits_opened_after_selection": True,
        "claim_boundary": (
            "A compact nonlinear correction was selected by holding out whole training "
            "families. Synthetic legacy splits are numerical probes only. Calibration, "
            "numerical-holdout and semantic-holdout families were evaluated only after "
            "candidate selection. This changed-arithmetic quality track makes no token-speed "
            "or model-quality claim."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": status, "selected": selected,
                      "evaluations": evaluations, "cartridge_bytes": len(payload),
                      "calculation_ms_p50": report["calculation_ms_p50"],
                      "canonical_sha256": report["canonical_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
