from __future__ import annotations
from typing import Any, Dict
import hashlib
from .stable_json import stable_stringify

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def make_replay_bundle(
    *,
    config: Dict[str, Any],
    metrics: Dict[str, Any],
    trace: Any,
    git_rev: str,
    run_id: str,
) -> Dict[str, Any]:
    created_utc = str(config.get("created_utc", "0000-00-00T00:00:00Z"))
    return {
        "schemaVersion": "GX1_REPLAY_BUNDLE_V0",
        "run_id": run_id,
        "git_rev": git_rev,
        "created_utc": created_utc,

        # Dataset provenance (duplicated at top-level for audit convenience)
        "dataset_id": str(config.get("dataset_id", "")),
        "dataset_sha256": str(config.get("dataset_sha256", "")),
        "preprocess_sha256": config.get("preprocess_sha256", None),

        "config": config,
        "metrics": metrics,
        "trace_digest": sha256_bytes(stable_stringify(trace).encode("utf-8")),
    }
