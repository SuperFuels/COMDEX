#!/usr/bin/env python3
"""Train a layer-specific nonlinear route-concentrated correction student."""
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


EXPERTS = 128
WIDTH = 2880


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


class RouteStudent(nn.Module):
    def __init__(self, hidden: int, embedding: int = 32) -> None:
        super().__init__()
        self.expert = nn.Embedding(EXPERTS, embedding)
        self.network = nn.Sequential(
            nn.Linear(WIDTH + embedding + 1, hidden), nn.GELU(),
            nn.Linear(hidden, hidden), nn.GELU(),
            nn.Linear(hidden, WIDTH),
        )

    def forward(self, activation: torch.Tensor, expert: torch.Tensor,
                gate: torch.Tensor) -> torch.Tensor:
        values = torch.cat((activation, self.expert(expert), gate[:, None]), dim=1)
        return self.network(values)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--augmentation-report", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--cartridge", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=12)
    parser.add_argument("--fit-family", default="arithmetic_real_48")
    parser.add_argument("--selection-family", default="extraction_real_48")
    parser.add_argument("--development-family", default="reasoning_real_40")
    parser.add_argument("--epochs", type=int, default=160)
    parser.add_argument("--seed", type=int, default=12022026)
    parser.add_argument("--expanded-fit", action="store_true")
    args = parser.parse_args()
    if args.cartridge.exists() or args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    authorization = json.loads(args.authorization.read_text())
    if authorization.get("authorized") is not True:
        raise SystemExit("explicit residual training authorization is absent")
    source = json.loads(args.source_manifest.read_text())
    source_path = Path(source["dataset_path"])
    if digest(source_path) != source["dataset_sha256"]:
        raise SystemExit("source dataset hash mismatch")
    augmentation = json.loads(args.augmentation_report.read_text())
    augmented_path = Path(augmentation["dataset_path"])
    if digest(augmented_path) != augmentation["dataset_sha256"]:
        raise SystemExit("augmentation dataset hash mismatch")
    fit_families = (augmentation["training_families"] if args.expanded_fit
                    else [args.fit_family])
    if augmentation["training_families"] != fit_families:
        raise SystemExit("augmentation does not match the declared fit family")
    arrays = dict(np.load(source_path))
    augmented = dict(np.load(augmented_path))
    rows = source["rows"]
    fit = np.asarray([i for i, row in enumerate(rows)
                      if int(row["layer"]) == args.layer
                      and row["family_id"] in fit_families])
    selection = np.asarray([i for i, row in enumerate(rows)
                            if int(row["layer"]) == args.layer
                            and row["family_id"] == args.selection_family])
    development = np.asarray([i for i, row in enumerate(rows)
                              if int(row["layer"]) == args.layer
                              and row["family_id"] == args.development_family])
    train_x = np.concatenate((np.asarray(arrays["router"])[fit], augmented["router"]))
    train_y = np.concatenate((np.asarray(arrays["omitted"])[fit], augmented["target"]))
    train_e = np.concatenate((
        np.asarray([rows[int(i)]["route"][3] for i in fit], dtype=np.int64),
        np.asarray(augmented["expert"], dtype=np.int64),
    ))
    train_g = np.concatenate((
        np.asarray([rows[int(i)]["gates"][3] for i in fit], dtype=np.float32),
        np.asarray(augmented["gate"], dtype=np.float32),
    ))
    mean = train_x.mean(0).astype(np.float32)
    scale = train_x.std(0).astype(np.float32)
    scale[scale < 1e-5] = 1.0
    target_scale = float(np.sqrt(np.mean(train_y.astype(np.float64) ** 2)))
    normalized_x = ((train_x - mean) / scale).astype(np.float32)
    normalized_y = (train_y / target_scale).astype(np.float32)
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    x_tensor = torch.from_numpy(normalized_x).to(device)
    y_tensor = torch.from_numpy(normalized_y).to(device)
    e_tensor = torch.from_numpy(train_e).to(device)
    g_tensor = torch.from_numpy(train_g).to(device)

    def evaluate(model: RouteStudent, indices: np.ndarray) -> dict:
        known = set(int(value) for value in train_e)
        selected = [int(i) for i in indices if int(rows[int(i)]["route"][3]) in known]
        if not selected:
            return {"covered_rows": 0, "errors": np.asarray([], dtype=np.float64)}
        values = ((np.asarray(arrays["router"])[selected] - mean) / scale).astype(np.float32)
        experts = np.asarray([rows[i]["route"][3] for i in selected], dtype=np.int64)
        gates = np.asarray([rows[i]["gates"][3] for i in selected], dtype=np.float32)
        with torch.no_grad():
            prediction = model(
                torch.from_numpy(values).to(device),
                torch.from_numpy(experts).to(device),
                torch.from_numpy(gates).to(device),
            ).cpu().numpy() * target_scale
        target = np.asarray(arrays["omitted"])[selected]
        layer_output = (np.asarray(arrays["ffn"])[selected]
                        + np.asarray(arrays["full"])[selected])
        errors = np.linalg.norm(prediction - target, axis=1) / np.maximum(
            np.linalg.norm(layer_output, axis=1), 1e-30,
        )
        return {"covered_rows": len(selected), "errors": errors}

    candidates = []
    models = []
    configurations = ((512, 1e-4),) if args.expanded_fit else (
        (256, 1e-4), (512, 1e-4), (512, 1e-3),
    )
    for candidate_index, (hidden, decay) in enumerate(configurations):
        torch.manual_seed(args.seed + candidate_index)
        model = RouteStudent(hidden).to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=8e-4,
                                      weight_decay=decay)
        for _ in range(args.epochs):
            optimizer.zero_grad(set_to_none=True)
            prediction = model(x_tensor, e_tensor, g_tensor)
            loss = torch.mean(torch.sum((prediction - y_tensor) ** 2, dim=1))
            loss.backward()
            optimizer.step()
        result = evaluate(model, development if args.expanded_fit else selection)
        errors = result["errors"]
        candidates.append({
            "hidden": hidden, "weight_decay": decay,
            "selection_rows": len(development) if args.expanded_fit else len(selection),
            "covered_rows": result["covered_rows"],
            "coverage": result["covered_rows"] /
                        (len(development) if args.expanded_fit else len(selection)),
            "relative_l2_p50": float(np.median(errors)),
            "relative_l2_p95": float(np.percentile(errors, 95)),
            "safe_rows": int(np.sum(errors <= 0.02)),
        })
        models.append(model.cpu())
    chosen_index = min(range(len(candidates)),
                       key=lambda i: candidates[i]["relative_l2_p95"])
    chosen = candidates[chosen_index]
    model = models[chosen_index].to(device).eval()
    result = evaluate(model, development)
    errors = result["errors"]
    timings = []
    sample = development[:1]
    for _ in range(100):
        started = time.perf_counter_ns()
        _ = evaluate(model, sample)
        timings.append((time.perf_counter_ns() - started) / 1e6)
    buffer = io.BytesIO()
    torch.save({
        "state_dict": model.cpu().state_dict(), "hidden": chosen["hidden"],
        "feature_mean": mean, "feature_scale": scale,
        "target_scale": target_scale, "known_experts": sorted(set(map(int, train_e))),
    }, buffer)
    args.cartridge.parent.mkdir(parents=True, exist_ok=True)
    args.cartridge.write_bytes(buffer.getvalue())
    safe = int(np.sum(errors <= 0.02))
    accepted = {
        "development_oracle_safe_coverage_at_least_10_percent": safe / len(development) >= 0.10,
        "development_p95_at_most_two_percent": (
            result["covered_rows"] == len(development)
            and float(np.percentile(errors, 95)) <= 0.02
        ),
        "cartridge_under_64_mib": args.cartridge.stat().st_size <= 64 * 1024 * 1024,
    }
    report = {
        "schema": "aion.gptoss-120b-route-concentrated-nonlinear-gate.v1",
        "status": ("ADVANCE_ROUTE_CONCENTRATED_NONLINEAR" if all(accepted.values())
                   else "STOP_ROUTE_CONCENTRATED_NONLINEAR"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "quality_track": True, "exact_fallback_required": True,
        "layer": args.layer, "fit_families": fit_families,
        "selection_family": args.selection_family,
        "development_family": args.development_family,
        "training_rows": len(train_x), "candidates": candidates,
        "selected": chosen, "development_rows": len(development),
        "development_covered_rows": result["covered_rows"],
        "development_safe_rows": safe,
        "development_oracle_safe_coverage": safe / len(development),
        "development_relative_l2_p50": float(np.median(errors)),
        "development_relative_l2_p95": float(np.percentile(errors, 95)),
        "development_relative_l2_max": float(np.max(errors)),
        "calculation_ms_p50": float(np.median(timings[10:])),
        "calculation_ms_p95": float(np.percentile(timings[10:], 95)),
        "cartridge_path": str(args.cartridge.resolve()),
        "cartridge_bytes": args.cartridge.stat().st_size,
        "cartridge_sha256": digest(args.cartridge),
        "source_manifest_canonical_sha256": source["canonical_sha256"],
        "augmentation_canonical_sha256": augmentation["canonical_sha256"],
        "authorization_sha256": digest(args.authorization),
        "acceptance": accepted,
        "claim_boundary": (
            "This layer-specific nonlinear student was trained only on the declared whole "
            "families and teacher-generated perturbations. In expanded-fit mode its "
            "architecture was frozen by the preceding arithmetic-to-extraction gate before "
            "extraction joined training; reasoning was opened once for development. Unknown "
            "experts and uncertified positions "
            "require the original fourth expert. Safe coverage is an oracle upper bound."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in (
        "status", "selected", "development_covered_rows", "development_safe_rows",
        "development_relative_l2_p50", "development_relative_l2_p95",
        "cartridge_bytes", "calculation_ms_p50", "canonical_sha256",
    )}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
