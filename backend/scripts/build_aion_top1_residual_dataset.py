#!/usr/bin/env python3
"""Build a hash-bound top-1 plus omitted-expert residual training dataset."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore


WIDTH = 2880


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def load(path: str | Path) -> np.ndarray:
    result = np.fromfile(path, dtype="<f4")
    if result.size != WIDTH:
        raise SystemExit(f"capture width mismatch: {path}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--retained-experts", type=int, choices=(1, 2, 3), default=1)
    args = parser.parse_args()
    if args.dataset.exists() or args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    authorization = json.loads(args.authorization.read_text())
    if (authorization.get("schema") !=
            "aion.gptoss-120b-residual-training-authorization.v1"
            or authorization.get("authorized") is not True):
        raise SystemExit("explicit residual training authorization is absent")
    source = json.loads(args.captures.read_text())
    if source.get("status") != "READY_FOR_AUTHORIZED_TRAINING":
        raise SystemExit("capture manifest is not training-ready")
    split = {family: name for name, families in source["family_disjoint_split"].items()
             for family in families}
    native = (Path(__file__).parents[1] /
              "modules/aion_inference/native/gptoss_persistent_moe_library.cpp")
    store = GptOssExpertFrameStore(args.manifest, 512 * 1024 * 1024)
    arrays = {name: [] for name in ("ffn", "router", "top1", "full", "omitted")}
    rows = []
    with tempfile.TemporaryDirectory(prefix="aion-top1-residual-dataset-") as temporary:
        library_path = Path(temporary) / "moe.dylib"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-dynamiclib",
            "-I/opt/homebrew/include", str(native), "-L/opt/homebrew/lib",
            "-lggml", "-lggml-base", "-ldl", "-o", str(library_path),
        ], check=True)
        library = ctypes.CDLL(str(library_path))
        function = library.aion_gptoss_moe_finish_active
        function.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_float),
            ctypes.c_int, ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
        ]
        function.restype = ctypes.c_int
        for family in source["families"]:
            for record in family["records"]:
                for name in ("ffn", "router", "residual"):
                    path = Path(record[f"{name}_path"])
                    if digest(path) != record[f"{name}_sha256"]:
                        raise SystemExit(f"capture hash mismatch: {path}")
                ffn = load(record["ffn_path"])
                router = load(record["router_path"])
                full = load(record["residual_path"])
                experts = store.get_layer_route_parallel(
                    record["layer"], record["route"][:args.retained_experts],
                    workers=args.retained_experts,
                )
                blobs = [expert[projection][kind] for expert in experts
                         for projection in ("gate", "up", "down")
                         for kind in ("weight", "bias")]
                references = [ctypes.c_char_p(blob) for blob in blobs]
                pointers = (ctypes.c_void_p * len(blobs))(*[
                    ctypes.cast(reference, ctypes.c_void_p).value
                    for reference in references
                ])
                gates = np.asarray(
                    record["gates"][:args.retained_experts], dtype=np.float32,
                )
                top1_output = np.empty(WIDTH, dtype=np.float32)
                elapsed = ctypes.c_double()
                status = function(
                    ffn.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    router.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), pointers,
                    gates.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    args.retained_experts,
                    top1_output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                    args.threads, ctypes.byref(elapsed),
                )
                if status:
                    raise RuntimeError(f"native top-1 status {status}")
                retained = top1_output - ffn
                values = {"ffn": ffn, "router": router, "top1": retained,
                          "full": full, "omitted": full - retained}
                index = len(rows)
                for name, value in values.items():
                    arrays[name].append(value)
                rows.append({
                    "index": index, "family_id": family["family_id"],
                    "split": split[family["family_id"]],
                    "position": record["position"], "layer": record["layer"],
                    "route": record["route"], "gates": record["gates"],
                    "retained_experts": args.retained_experts,
                    "retained_compute_ms": elapsed.value,
                })
    args.dataset.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.dataset, **{
        name: np.stack(values).astype("<f4") for name, values in arrays.items()
    })
    report = {
        "schema": "aion.gptoss-120b-top1-residual-dataset.v1",
        "status": "READY_FOR_AUTHORIZED_RESIDUAL_TRAINING",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "dataset_path": str(args.dataset.resolve()),
        "dataset_sha256": digest(args.dataset), "rows": rows,
        "row_count": len(rows), "width": WIDTH,
        "retained_experts": args.retained_experts,
        "source_manifest_path": str(args.captures.resolve()),
        "source_manifest_canonical_sha256": source["canonical_sha256"],
        "authorization_sha256": digest(args.authorization),
        "warehouse_metrics": store.metrics(),
        "contains_prompt_text": False,
        "contains_personal_or_customer_data": False,
        "claim_boundary": (
            "Every row contains the original retained-expert contribution and the exact "
            "combined gated contribution omitted from the remaining routed experts, derived from "
            "previously frozen numerical captures. This authorizes quality-track "
            "training only and is not model-quality or token-speed evidence."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": report["status"], "rows": len(rows),
        "dataset_bytes": args.dataset.stat().st_size,
        "canonical_sha256": report["canonical_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
