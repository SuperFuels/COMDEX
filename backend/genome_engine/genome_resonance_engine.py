from __future__ import annotations
from typing import Any, Dict, List
import hashlib

from .dataset_loader import load_jsonl_dataset
from .genomics_codec import encode_dna, mapping_table
from .genomics_metrics import rho_from_tokens, crosstalk_matrix, drift_mean


def _hash8(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


def deterministic_run_id(cfg: Dict[str, Any]) -> str:
    """
    Deterministic run_id derived from config (excluding volatile fields).
    NOTE: output_root is intentionally included in the hash unless caller overrides run_id.
    """
    import json

    seed = int(cfg.get("seed", 0))
    hcfg = dict(cfg)
    hcfg.pop("run_id", None)
    hcfg.pop("created_utc", None)

    # stable-ish: sort keys recursively
    def _stabilize(x: Any) -> Any:
        if x is None or isinstance(x, (bool, int, float, str)):
            return x
        if isinstance(x, list):
            return [_stabilize(v) for v in x]
        if isinstance(x, dict):
            return {str(k): _stabilize(x[k]) for k in sorted(x.keys())}
        return str(x)

    blob = json.dumps(_stabilize(hcfg), separators=(",", ":"), ensure_ascii=False)
    h = _hash8(blob)
    return f"P21_GX1_{h}_S{seed}"


def run_sim_core(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic SIM-core baseline.

    TRACE CONTRACT (v0):
      - Only two event kinds are emitted:
          1) trace_kind="scenario_summary"
          2) trace_kind="rho_trace_eval_window"
      - One pair per scenario (so TRACE stays small).
    """
    dataset_path = cfg["dataset_path"]
    mapping_id = str(cfg.get("mapping_id", "GX1_MAP_V1"))
    chip_mode = str(cfg.get("chip_mode", "ONEHOT4"))

    thresholds = cfg.get("thresholds", {}) or {}
    warmup = int(thresholds.get("warmup_ticks", 128))
    eval_ticks = int(thresholds.get("eval_ticks", 512))

    rows = load_jsonl_dataset(dataset_path)
    if not rows:
        raise ValueError(f"Dataset empty: {dataset_path}")

    scenarios = cfg.get("scenarios") or [{"scenario_id": "matched_key", "mode": "matched", "k": 1, "mutation": None}]

    row0 = rows[0]
    seq = str(row0.get("seq") or row0.get("sequence") or "")
    tx_stream = encode_dna(seq, mapping_id=mapping_id, chip_mode=chip_mode)

    out_summaries: Dict[str, Any] = {}
    trace_events: List[Dict[str, Any]] = []

    # choose a deterministic sim length bounded by the message
    total_len = max(warmup + eval_ticks, min(len(tx_stream), 2048))

    for sc in scenarios:
        sid = str(sc.get("scenario_id", "scenario"))
        mode = str(sc.get("mode", "matched"))
        k = int(sc.get("k", 1))
        mut = sc.get("mutation") or None

        # Build per-channel RX streams (deterministic transforms)
        rx_streams: List[List[int]] = []
        for ch in range(k):
            rx = list(tx_stream)

            if mode == "mismatch":
                rx = [((t + 1) % 4) for t in rx]

            if mode == "multiplex":
                # deliberately separable channels
                if ch > 0:
                    rx = [((t + (ch % 4)) % 4) for t in rx]

            if mode == "mutation" and mut:
                tgt = int(mut.get("target_channel", 0))
                sev = int(mut.get("severity", 0))
                if ch == tgt and sev > 0:
                    # corrupt first sev positions deterministically
                    rx = [((t + 2) % 4) if i < sev else t for i, t in enumerate(rx)]

            rx_streams.append(rx)

        # Deterministic rho_trace (contract: eval window only)
        rho_trace: List[float] = []
        for tick in range(total_len):
            if mode == "matched":
                rho_trace.append(0.2 + 0.8 * min(1.0, tick / max(1, warmup)))
            elif mode == "multiplex":
                rho_trace.append(0.25 + 0.55 * min(1.0, tick / max(1, warmup)))
            elif mode == "mutation":
                if tick < warmup // 2:
                    rho_trace.append(0.2 + 0.8 * min(1.0, tick / max(1, warmup)))
                else:
                    rho_trace.append(0.1)
            else:
                rho_trace.append(0.15)

        eval_window = rho_trace[-eval_ticks:] if eval_ticks > 0 else list(rho_trace)
        coherence_mean = float(sum(eval_window) / max(1, len(eval_window)))
        drift = float(drift_mean(rho_trace, warmup=warmup))

        rho_primary = float(rho_from_tokens(tx_stream, rx_streams[0])) if rx_streams else 0.0

        cm = crosstalk_matrix(rx_streams) if k > 1 else [[1.0]]
        crosstalk_max = 0.0
        if k > 1:
            for i in range(k):
                for j in range(k):
                    if i != j:
                        crosstalk_max = max(crosstalk_max, float(cm[i][j]))

        out_summaries[sid] = {
            "scenario_id": sid,
            "mode": mode,
            "k": k,
            "rho_primary": float(rho_primary),
            "coherence_mean": float(coherence_mean),
            "drift_mean": float(drift),
            "crosstalk_max": float(crosstalk_max),
            "rho_trace": eval_window,
        }

        # TRACE (2 events only)
        trace_events.append({
            "trace_kind": "scenario_summary",
            "scenario_id": sid,
            "mode": mode,
            "k": k,
            "rho_primary": float(rho_primary),
            "coherence_mean": float(coherence_mean),
            "drift_mean": float(drift),
            "crosstalk_max": float(crosstalk_max),
        })
        trace_events.append({
            "trace_kind": "rho_trace_eval_window",
            "scenario_id": sid,
            "warmup_ticks": warmup,
            "eval_ticks": eval_ticks,
            "rho_trace": eval_window,
        })

    return {
        "mapping": mapping_table(mapping_id),
        "dataset_row_id": str(row0.get("id", "row0")),
        "scenario_summaries": out_summaries,
        "trace": trace_events,
    }
