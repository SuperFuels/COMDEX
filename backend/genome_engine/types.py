from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict

Json = Any

class DatasetRow(TypedDict, total=False):
    id: str
    seq: str
    label: Optional[str]
    channel_key: Optional[str]
    mutation: Optional[Dict[str, Any]]

class Thresholds(TypedDict, total=False):
    warmup_ticks: int
    eval_ticks: int
    rho_matched_min: float
    rho_mismatch_abs_max: float
    crosstalk_max: float
    coherence_mean_min: float
    drift_mean_max: float

class GX1Config(TypedDict, total=False):
    schemaVersion: str
    objective_id: str
    seed: int
    created_utc: str
    note: str

    dataset_path: str
    output_root: str
    run_id: str

    dt: float
    steps: int

    mapping_id: str
    chip_mode: str

    scenarios: List[Dict[str, Any]]
    thresholds: Thresholds

@dataclass(frozen=True)
class EngineRun:
    run_id: str
    git_rev: str
    out_root: str
    run_dir: str
