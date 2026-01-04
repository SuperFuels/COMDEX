from backend.genome_engine.sle_adapter import SLEAdapter
import json

thresholds = {"warmup_ticks": 16, "eval_ticks": 32}
scenarios = [
    {"scenario_id": "matched_key", "mode": "matched", "k": 1},
    {"scenario_id": "mux_2", "mode": "multiplex", "k": 2},
]

a1 = SLEAdapter(seed=7, dt=1/30)
r1 = a1.run(scenarios=scenarios, thresholds=thresholds)
a2 = SLEAdapter(seed=7, dt=1/30)
r2 = a2.run(scenarios=scenarios, thresholds=thresholds)

t1, t2 = r1["trace"], r2["trace"]
for idx, (e1, e2) in enumerate(zip(t1, t2)):
    if e1 != e2:
        print("first mismatch idx:", idx)
        kset = set(e1.keys()) | set(e2.keys())
        diffs = {k: (e1.get(k), e2.get(k)) for k in sorted(kset) if e1.get(k) != e2.get(k)}
        print(json.dumps(diffs, indent=2, default=str))
        break
else:
    print("no mismatch in shared prefix; lengths:", len(t1), len(t2))