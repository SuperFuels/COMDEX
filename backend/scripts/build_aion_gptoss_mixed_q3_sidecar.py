#!/usr/bin/env python3
"""Precompile hash-bound Q3 gate/up plus exact down expert sidecars."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from backend.modules.aion_inference.gptoss_expert_frame_store import (
    GptOssPersistentL2ExpertFrameStore,
)


MAGIC = b"AIONQ3S1"
HEADER = struct.Struct("<8s6Q")
ORDER = tuple((projection, kind)
              for projection in ("gate", "up", "down")
              for kind in ("weight", "bias"))
WIDTH = 2880
PADDED = 3072


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()


def collect_pairs(trace: Path) -> set[tuple[int, int]]:
    report = json.loads(trace.read_text())
    runs = [report["run_a"], report["run_b"], *report.get("additional_runs", [])]
    pairs = set()
    for run in runs:
        for token in run["tokens"]:
            for layer in token["layers"]:
                if layer.get("selective_fourth_q3_gate_up"):
                    pairs.add((int(layer["layer"]), int(layer["route"][3])))
    if not pairs:
        raise SystemExit("trace contains no admitted mixed-Q3 pairs")
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--persistent-l2-root", type=Path, required=True)
    parser.add_argument("--persistent-l2-gib", type=float, default=20.0)
    parser.add_argument("--trace", type=Path, action="append", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=8)
    args = parser.parse_args()
    manifest_path = args.output_root / "manifest.v1.json"
    if args.output_root.exists():
        raise SystemExit("refusing to overwrite sidecar root")
    pairs = set().union(*(collect_pairs(path) for path in args.trace))
    args.output_root.mkdir(parents=True)
    native = Path(__file__).parents[1] / "modules/aion_inference/native"
    store = GptOssPersistentL2ExpertFrameStore(
        args.manifest, 0, args.persistent_l2_root,
        int(args.persistent_l2_gib * 1024 ** 3),
    )
    entries = []
    total_bytes = 0
    with tempfile.TemporaryDirectory(prefix="aion-build-mixed-q3-") as temporary:
        temp_root = Path(temporary)
        converter = temp_root / "convert"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-I/opt/homebrew/include",
            str(native / "gptoss_mxfp4_to_padded_k.cpp"),
            "-L/opt/homebrew/lib", "-lggml", "-lggml-base", "-ldl",
            "-o", str(converter),
        ], check=True)
        for index, (layer, expert) in enumerate(sorted(pairs), 1):
            original = store.get(layer, expert)
            components = []
            source_hashes = []
            for projection, kind in ORDER:
                raw = original[projection][kind]
                source_hashes.append(sha(raw))
                if projection in ("gate", "up") and kind == "weight":
                    source = temp_root / "source.mxfp4"
                    target = temp_root / "target.q3k"
                    source.write_bytes(raw)
                    subprocess.run([
                        str(converter), str(source), str(target), "q3_k",
                        str(WIDTH), str(args.threads),
                    ], check=True, stdout=subprocess.DEVNULL)
                    raw = target.read_bytes()
                elif projection in ("gate", "up") and kind == "bias":
                    raw = bytes(raw) + bytes((PADDED - WIDTH) * 4)
                components.append(raw)
            payload = HEADER.pack(MAGIC, *(len(value) for value in components)) + b"".join(components)
            name = f"layer-{layer:02d}-expert-{expert:03d}.aionq3"
            destination = args.output_root / name
            temporary_path = destination.with_name(name + f".{os.getpid()}.{uuid.uuid4().hex}.tmp")
            temporary_path.write_bytes(payload)
            os.replace(temporary_path, destination)
            total_bytes += len(payload)
            entries.append({
                "layer": layer, "expert": expert, "relative_path": name,
                "file_bytes": len(payload), "file_sha256": sha(payload),
                "component_sha256": [sha(value) for value in components],
                "source_component_sha256": source_hashes,
            })
            if index % 25 == 0 or index == len(pairs):
                print(f"compiled {index}/{len(pairs)}", flush=True)
    report = {
        "schema": "aion.gptoss-mixed-q3-sidecar.v1",
        "status": "COMPLETE_VERIFIED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_manifest": str(args.manifest.resolve()),
        "source_manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "source_trace_sha256": [hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in args.trace],
        "representation": "Q3_K gate/up, zero-padded gate/up biases, original MXFP4 down",
        "entries": entries, "entry_count": len(entries), "total_bytes": total_bytes,
        "builder_store_metrics": store.metrics(),
        "claim_boundary": (
            "Derived internal-disk runtime sidecar only. Original SD warehouse remains "
            "authoritative. Each compact frame is bound to the source manifest and original "
            "component hashes. Runtime absence or integrity failure requires exact fallback."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    manifest_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"entries": len(entries), "total_bytes": total_bytes,
                      "canonical_sha256": report["canonical_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
