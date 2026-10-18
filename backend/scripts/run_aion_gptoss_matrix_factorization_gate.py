#!/usr/bin/env python3
"""Factor the actual matrices of one routed GPT-OSS expert and test real activations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.utils.extmath import randomized_svd

from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore


WIDTH = 2880


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--activations", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=15)
    parser.add_argument("--expert", type=int, default=33)
    parser.add_argument("--ranks", default="32,64,128")
    parser.add_argument("--seed", type=int, default=1200911)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    ranks = sorted({int(value) for value in args.ranks.split(",")})
    if not ranks or ranks[0] < 1 or ranks[-1] >= WIDTH:
        raise SystemExit("invalid ranks")
    captures = []
    for path in sorted(args.activations.glob(f"position-*-layer-{args.layer}.json")):
        capture = json.loads(path.read_text())
        if args.expert in capture["route"]:
            captures.append((path, capture))
    if len(captures) < 2:
        raise SystemExit("expert must have at least two real activation captures")

    store = GptOssExpertFrameStore(args.manifest, 64 * 1024 * 1024)
    value = store.get(args.layer, args.expert)
    native = Path(__file__).parents[1] / "modules/aion_inference/native"
    observations = {str(rank): [] for rank in ranks}
    decomposition = {}
    with tempfile.TemporaryDirectory(prefix="aion-gptoss-matrix-factor-") as temporary:
        root = Path(temporary)
        dequantize = root / "dequantize"
        factorized = root / "factorized"
        original = root / "original"
        common = ["clang++", "-std=c++17", "-O3", "-I/opt/homebrew/include"]
        libraries = ["-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl"]
        subprocess.run([*common, str(native / "gptoss_mxfp4_dequantize.cpp"),
                        *libraries, "-o", str(dequantize)], check=True)
        subprocess.run([*common, str(native / "gptoss_factorized_expert_cpu_gate.cpp"),
                        *libraries, "-o", str(factorized)], check=True)
        subprocess.run([*common, str(native / "gptoss_packed_expert_cpu_gate.cpp"),
                        *libraries, "-o", str(original)], check=True)

        component_paths = {}
        matrices = {}
        for projection in ("gate", "up", "down"):
            for kind in ("weight", "bias"):
                path = root / f"{projection}-{kind}.bin"
                path.write_bytes(value[projection][kind])
                component_paths[(projection, kind)] = path
            f32_path = root / f"{projection}-f32.bin"
            subprocess.run([str(dequantize), str(component_paths[(projection, "weight")]),
                            str(f32_path), str(WIDTH), "8"], check=True,
                           stdout=subprocess.DEVNULL)
            matrices[projection] = np.memmap(f32_path, dtype="<f4", mode="r",
                                               shape=(WIDTH, WIDTH))

        max_rank = ranks[-1]
        factors = {}
        for projection, matrix in matrices.items():
            u, singular, vt = randomized_svd(
                matrix, n_components=max_rank, n_iter=2,
                random_state=args.seed + (0 if projection == "gate" else 1 if projection == "up" else 2),
            )
            decomposition[projection] = {
                "singular_values_first": float(singular[0]),
                "singular_values_last": float(singular[-1]),
                "captured_frobenius_fraction_at_ranks": {
                    str(rank): float(np.square(singular[:rank]).sum()
                                     / np.square(matrix).sum()) for rank in ranks
                },
            }
            factors[projection] = (u, singular, vt)

        original_weight_bytes = sum(len(value[p]["weight"]) for p in ("gate", "up", "down"))
        for capture_path, capture in captures:
            stem = capture_path.with_suffix("")
            input_path = Path(str(stem) + "-ffn.bin")
            reference_path = root / f"reference-{capture['position']}.bin"
            environment = {**os.environ, "AION_INPUT_PATH": str(input_path),
                           "AION_OUTPUT_PATH": str(reference_path)}
            subprocess.run([
                str(original),
                str(component_paths[("gate", "weight")]), str(component_paths[("gate", "bias")]),
                str(component_paths[("up", "weight")]), str(component_paths[("up", "bias")]),
                str(component_paths[("down", "weight")]), str(component_paths[("down", "bias")]),
                "1", "8",
            ], env=environment, check=True, stdout=subprocess.DEVNULL)
            reference = np.fromfile(reference_path, dtype="<f4").astype(np.float64)
            for rank in ranks:
                arguments = []
                factor_bytes = 0
                for projection in ("gate", "up", "down"):
                    u, singular, vt = factors[projection]
                    root_s = np.sqrt(singular[:rank])
                    v = (root_s[:, None] * vt[:rank]).astype("<f2")
                    uf = (u[:, :rank] * root_s[None, :]).astype("<f2")
                    v_path = root / f"{projection}-v-r{rank}.bin"
                    u_path = root / f"{projection}-u-r{rank}.bin"
                    if not v_path.exists():
                        v.tofile(v_path); uf.tofile(u_path)
                    arguments.extend((str(v_path), str(u_path),
                                      str(component_paths[(projection, "bias")])))
                    factor_bytes += v.nbytes + uf.nbytes
                candidate_path = root / f"candidate-p{capture['position']}-r{rank}.bin"
                subprocess.run([str(factorized), *arguments, str(input_path),
                                str(candidate_path), str(rank)], check=True,
                               stdout=subprocess.DEVNULL)
                candidate = np.fromfile(candidate_path, dtype="<f4").astype(np.float64)
                delta = candidate - reference
                observations[str(rank)].append({
                    "capture": capture_path.name, "position": capture["position"],
                    "output_relative_l2": float(np.linalg.norm(delta) / np.linalg.norm(reference)),
                    "output_max_abs": float(np.abs(delta).max()),
                    "argmax_equal": int(np.argmax(candidate)) == int(np.argmax(reference)),
                    "factor_bytes": factor_bytes,
                    "weight_reduction": original_weight_bytes / factor_bytes,
                })

    summaries = {}
    advancing = []
    for rank in ranks:
        rows = observations[str(rank)]
        summary = {
            "rank": rank,
            "samples": len(rows),
            "weight_reduction": rows[0]["weight_reduction"],
            "output_relative_l2_max": max(row["output_relative_l2"] for row in rows),
            "output_relative_l2_mean": float(np.mean([row["output_relative_l2"] for row in rows])),
            "all_argmax_equal": all(row["argmax_equal"] for row in rows),
        }
        summaries[str(rank)] = summary
        if (summary["weight_reduction"] >= 5.0
                and summary["output_relative_l2_max"] <= .02
                and summary["all_argmax_equal"]):
            advancing.append(rank)
    report = {
        "schema": "aion.gptoss-120b-actual-matrix-factorization-gate.v1",
        "status": "ADVANCE_MATRIX_FACTORIZATION" if advancing else "STOP_MATRIX_FACTORIZATION",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4", "quality_track": True,
        "layer": args.layer, "expert": args.expert, "ranks": ranks,
        "capture_paths": [str(path.resolve()) for path, _ in captures],
        "capture_hashes": {path.name: sha256_file(path) for path, _ in captures},
        "warehouse_manifest_sha256": sha256_file(args.manifest),
        "original_weight_bytes": original_weight_bytes,
        "factor_type": "float16 truncated randomized SVD of each actual gate/up/down matrix",
        "decomposition": decomposition, "observations": observations,
        "summaries": summaries, "advancing_ranks": advancing,
        "promotion_gate": {"minimum_weight_reduction": 5.0,
                           "maximum_output_relative_l2": .02,
                           "all_output_argmax_equal": True},
        "warehouse_metrics": store.metrics(),
        "claim_boundary": (
            "The actual three matrices of one original routed expert are dequantized and "
            "factorized independently of activations. Evaluation uses two frozen real activations. "
            "F16 factors are executed through GGML with the original biases and SwiGLU-OAI. This "
            "is a one-expert quality microgate, not a full layer, semantic result, compact warehouse, "
            "or generated-token speed claim."
        ),
    }
    report["canonical_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "summaries": summaries,
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
