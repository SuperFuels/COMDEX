from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).parents[2]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_manifest_and_exact_fallback_evaluator(tmp_path: Path) -> None:
    family_args = []
    for family_index in range(4):
        family_id = f"synthetic_{family_index}"
        directory = tmp_path / family_id
        directory.mkdir()
        stem = directory / "position-0-layer-0"
        ffn = np.full(2880, family_index, dtype="<f4")
        router = np.full(2880, family_index + 1, dtype="<f4")
        residual = np.full(2880, family_index + 2, dtype="<f4")
        output = ffn + residual
        for name, value in (("ffn", ffn), ("router", router),
                            ("residual", residual), ("output", output)):
            value.tofile(Path(str(stem) + f"-{name}.bin"))
        metadata = {
            "schema": "aion.gptoss-120b-shadow-target-capture.v2",
            "position": 0, "layer": 0, "route": [0, 1, 2, 3],
            "gates": [.4, .3, .2, .1],
            "target_definition": "test F32 residual",
            "contains_prompt_text": False,
            "contains_personal_or_customer_data": False,
        }
        for name in ("ffn", "router", "residual", "output"):
            metadata[f"{name}_sha256"] = sha(Path(str(stem) + f"-{name}.bin"))
        Path(str(stem) + ".json").write_text(json.dumps(metadata))
        family_args.extend(("--family", f"{family_id}={directory}"))

    manifest = tmp_path / "manifest.json"
    subprocess.run([
        sys.executable, str(ROOT / "backend/scripts/build_aion_shadow_expert_dataset_manifest.py"),
        *family_args, "--output", str(manifest),
    ], check=True)
    manifest_data = json.loads(manifest.read_text())
    assert manifest_data["status"] == "READY_FOR_AUTHORIZED_TRAINING"
    assert manifest_data["all_records_have_verified_targets"] is True
    assert manifest_data["training_authorized"] is False

    candidate = tmp_path / "candidate"
    candidate.mkdir()
    holdout = (manifest_data["family_disjoint_split"]["numerical_holdout"] +
               manifest_data["family_disjoint_split"]["semantic_holdout"])
    by_family = {item["family_id"]: item for item in manifest_data["families"]}
    for family_id in holdout:
        record = by_family[family_id]["records"][0]
        prediction = candidate / f"{family_id}--position-0--layer-0-prediction.bin"
        prediction.write_bytes(Path(record["residual_path"]).read_bytes())
        receipt = candidate / f"{family_id}--position-0--layer-0-confidence.json"
        receipt.write_text(json.dumps({"confidence": 1.0,
                                       "prediction_sha256": sha(prediction)}))
    evaluation = tmp_path / "evaluation.json"
    subprocess.run([
        sys.executable, str(ROOT / "backend/scripts/evaluate_aion_shadow_expert_fallback.py"),
        "--manifest", str(manifest), "--candidate-dir", str(candidate),
        "--confidence-threshold", "0.9", "--output", str(evaluation),
    ], check=True)
    result = json.loads(evaluation.read_text())
    assert result["status"] == "MECHANISM_GATE_FAILED"
    assert result["summary"]["relative_l2_max"] == 0.0
    # Two holdout samples cannot prove the predeclared 10x traffic gate, even
    # with oracle predictions. This guards against tiny-corpus promotion.
    assert result["summary"]["projected_expert_traffic_reduction"] == 2.0
    assert result["summary"]["holdout_observations_sufficient"] is False
    assert "INSUFFICIENT_HOLDOUT_OBSERVATIONS" in result["failure_reasons"]
