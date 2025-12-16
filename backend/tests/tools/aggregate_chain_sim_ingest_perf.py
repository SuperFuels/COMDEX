from __future__ import annotations

import json
from pathlib import Path

def main() -> None:
    root = Path(__file__).resolve().parents[1] / "artifacts"
    files = sorted(root.glob("glyphchain_ingest_perf_*.json"))

    rows = []
    for p in files:
        if p.name.endswith("_latest.json"):
            continue
        try:
            j = json.loads(p.read_text())
        except Exception:
            continue

        env = j.get("env") or {}
        rows.append({
            "max_tx": int(env.get("CHAIN_SIM_BLOCK_MAX_TX", 0) or 0),
            "max_ms": int(env.get("CHAIN_SIM_BLOCK_MAX_MS", 0) or 0),
            "mode": j.get("mode"),
            "persist": 1 if str(env.get("CHAIN_SIM_PERSIST", "0")) == "1" else 0,
            "n": int(j.get("n", 0) or 0),
            "tps_ingest": float(j.get("tps_ingest", 0.0) or 0.0),
            "tps_finalized": float(j.get("tps_finalized", 0.0) or 0.0),
            "p50_ms": float((j.get("lat_ms") or {}).get("p50", 0.0) or 0.0),
            "p95_ms": float((j.get("lat_ms") or {}).get("p95", 0.0) or 0.0),
            "p99_ms": float((j.get("lat_ms") or {}).get("p99", 0.0) or 0.0),
            "file": p.name,
        })

    rows.sort(key=lambda r: (r["max_tx"], r["max_ms"], r["mode"], r["file"]))

    print("| max_tx | max_ms | mode | persist | n | tps_ingest | tps_finalized | p50_ms | p95_ms | p99_ms | file |")
    print("|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for r in rows:
        print(
            f'| {r["max_tx"]} | {r["max_ms"]} | {r["mode"]} | {r["persist"]} | {r["n"]} | '
            f'{r["tps_ingest"]:.2f} | {r["tps_finalized"]:.2f} | '
            f'{r["p50_ms"]:.3f} | {r["p95_ms"]:.3f} | {r["p99_ms"]:.3f} | {r["file"]} |'
        )

if __name__ == "__main__":
    main()