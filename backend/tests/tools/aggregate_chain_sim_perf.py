import json
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "artifacts"

def main():
    files = sorted(ART.glob("glyphchain_perf_*.json"))
    files = [p for p in files if p.name != "glyphchain_perf_latest.json"]

    if not files:
        print(f"No perf snapshots found in {ART}. Run the sweep first.")
        return

    rows = []
    for p in files:
        j = json.loads(p.read_text())
        env = j.get("env") or {}
        avg = j.get("avg_seconds") or {}

        rows.append({
            "file": p.name,
            "mode": j.get("mode"),
            "max_tx": env.get("CHAIN_SIM_BLOCK_MAX_TX"),
            "max_ms": env.get("CHAIN_SIM_BLOCK_MAX_MS"),
            "persist": env.get("CHAIN_SIM_PERSIST"),
            "n": j.get("n"),
            "state_ms": float(avg.get("GET /api/chain_sim/dev/state", 0.0)) * 1000.0,
            "supply_ms": float(avg.get("GET /api/chain_sim/dev/supply", 0.0)) * 1000.0,
        })

    rows.sort(key=lambda r: (int(r["max_tx"]), int(r["max_ms"]), r["mode"] or ""))

    # print a simple markdown table
    print("| max_tx | max_ms | mode | persist | n | state_ms | supply_ms | file |")
    print("|---:|---:|---|---:|---:|---:|---:|---|")
    for r in rows:
        print(
            f'| {r["max_tx"]} | {r["max_ms"]} | {r["mode"]} | {r["persist"]} | {r["n"]} | '
            f'{r["state_ms"]:.3f} | {r["supply_ms"]:.3f} | {r["file"]} |'
        )

if __name__ == "__main__":
    main()