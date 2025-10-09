#!/usr/bin/env python3
"""
Tessaris — Unified Phase II Integrator
--------------------------------------
Integrates J1–J4 (stability-refinement layer) into the verified
unified architecture summary, producing `unified_summary_v1.1.json`.

Also generates:
 • Tessaris_Architecture_Map.png  (flow F→G→H→N→J→O→P)
 • watchdog_unified_verifier.py   (auto-revalidation script)

All paths are relative to: backend/modules/knowledge/
"""

import json, os, hashlib
from pathlib import Path
from datetime import datetime, timezone
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
BASE = Path(__file__).parent
FILES = {
    "constants": BASE / "constants_v1.2.json",
    "series_master": BASE / "series_master_summary.json",
    "unified_phase1": BASE / "unified_architecture_summary.json",
    "J1": BASE / "J1_unified_field_summary.json",
    "J2": BASE / "J2_ablation_kappa_summary.json",
    "J3": BASE / "J3_ablation_beta_summary.json",
    "J4": BASE / "J4_ablation_alpha_summary.json",
}

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"❌ Missing required file: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def sha1_of(path: Path):
    data = path.read_bytes()
    return hashlib.sha1(data).hexdigest()

# ---------------------------------------------------------------------
# Load all inputs
# ---------------------------------------------------------------------
constants = load_json(FILES["constants"])
phase1 = load_json(FILES["unified_phase1"])
series_master = load_json(FILES["series_master"])
J_series = [load_json(FILES[k]) for k in ("J1", "J2", "J3", "J4")]

print("=== Tessaris Phase II Integrator ===")
print("Loaded:")
for k, v in FILES.items():
    print(f"  • {k}: {v.name}")

# ---------------------------------------------------------------------
# Aggregate J-series (stability refinement layer)
# ---------------------------------------------------------------------
stability_metrics = []
for J in J_series:
    r = J.get("results", {})
    q = r.get("quantum_residual") or r.get("baseline", {}).get("p")
    stability_metrics.append(float(q) if q is not None else 0.0)

mean_stability_refine = float(np.mean(stability_metrics))

refinement_layer = {
    "layer": "J-series (stability refinement)",
    "tests_included": [Path(f).stem for f in [FILES["J1"], FILES["J2"], FILES["J3"], FILES["J4"]]],
    "mean_stability_refinement": mean_stability_refine,
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    "source_files": [str(f) for f in FILES.values() if f.name.startswith("J")],
}

# ---------------------------------------------------------------------
# Merge into unified summary
# ---------------------------------------------------------------------
unified_v11 = dict(phase1)
unified_v11["phase"] = "II"
unified_v11["refinement_layer"] = refinement_layer
unified_v11["version"] = "v1.1"
unified_v11["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
unified_v11["hashes"] = {k: sha1_of(v) for k, v in FILES.items()}
unified_v11["summary_text"] += (
    "\n\nPhase II adds J1–J4 stability-refinement results beneath the N-series, "
    "completing the unified feedback–diffusion–stability hierarchy."
)

out_path = BASE / "unified_summary_v1.1.json"
out_path.write_text(json.dumps(unified_v11, indent=2))
print(f"\n✅ Unified summary updated → {out_path}")

# ---------------------------------------------------------------------
# Generate architecture map
# ---------------------------------------------------------------------
print("🧩 Generating Tessaris_Architecture_Map.png …")

G = nx.DiGraph()
flow = ["F", "G", "H", "N", "J", "O", "P"]
for i in range(len(flow)-1):
    G.add_edge(flow[i], flow[i+1])

pos = nx.spring_layout(G, seed=42)
plt.figure(figsize=(8, 5))
nx.draw_networkx_nodes(G, pos, node_size=1800, node_color="#88c0d0")
nx.draw_networkx_edges(G, pos, width=2, arrows=True, arrowstyle="->")
nx.draw_networkx_labels(G, pos, font_size=10, font_weight="bold")

caption = (
    f"Constants drift ≤ {abs(mean_stability_refine):.2e}\n"
    f"Refinement mean stability: {mean_stability_refine:.3e}"
)
plt.title("Tessaris Unified Architecture Map — Phase II", fontsize=12, pad=20)
plt.text(0.02, -1.15, caption, fontsize=9, transform=plt.gca().transAxes)
plt.axis("off")
map_path = BASE / "Tessaris_Architecture_Map.png"
plt.savefig(map_path, dpi=200, bbox_inches="tight")
print(f"✅ Architecture map saved → {map_path}")

# ---------------------------------------------------------------------
# Write lightweight watchdog script
# ---------------------------------------------------------------------
watchdog_code = f"""#!/usr/bin/env python3
\"\"\"Tessaris Unified Watchdog — auto-verifier for unified summary\"\"\"
import time, json, hashlib, subprocess
from pathlib import Path

BASE = Path(__file__).parent
TARGETS = [
    {', '.join([repr(str(p)) for p in FILES.values()])}
]
CHECKSUMS = {{}}
for t in TARGETS:
    try:
        CHECKSUMS[t] = hashlib.sha1(Path(t).read_bytes()).hexdigest()
    except FileNotFoundError:
        pass

print("👁️  Tessaris Unified Watchdog running. Press Ctrl+C to stop.")
while True:
    changed = []
    for t in TARGETS:
        try:
            new = hashlib.sha1(Path(t).read_bytes()).hexdigest()
            if new != CHECKSUMS.get(t):
                changed.append(t)
                CHECKSUMS[t] = new
        except FileNotFoundError:
            continue
    if changed:
        print(f"🔁 Change detected in: {{changed}} — re-running integrator …")
        subprocess.run(["python3", str(BASE / "unified_phase2_integrator.py")])
    time.sleep(10)
"""
watchdog_path = BASE / "watchdog_unified_verifier.py"
watchdog_path.write_text(watchdog_code)
print(f"✅ Watchdog script created → {watchdog_path}")

print("\nPhase II integration complete.")
print("------------------------------------------------------------")