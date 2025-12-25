import json, os, sys

LOCK = "INERTIA/LOCKED_RUNS.json"

def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def show(test_id, run_hash):
    base = f"INERTIA/artifacts/programmable_inertia/{test_id}/{run_hash}"
    for req in ("run.json", "meta.json", "config.json", "metrics.csv"):
        p = os.path.join(base, req)
        if not os.path.exists(p):
            raise SystemExit(f"[FAIL] missing {p}")
    run  = load(os.path.join(base, "run.json"))
    meta = load(os.path.join(base, "meta.json"))
    cfg  = load(os.path.join(base, "config.json"))

    print(
        f"{test_id} {run_hash} {meta.get('controller')}"
        f" v_target={run.get('v_target')}"
        f" v_final={run.get('v_final')}"
        f" err_final={run.get('err_final')}"
        f" alpha0={cfg.get('alpha0')}"
        f" alpha_final={run.get('alpha_final')}"
    )

def main():
    lock = load(LOCK)
    for test_id, controllers in lock["pinned_runs"].items():
        for _, rh in controllers.items():
            show(test_id, rh)
    print("[OK] pinned artifacts present")

if __name__ == "__main__":
    main()
