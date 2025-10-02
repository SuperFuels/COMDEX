# backend/photon_algebra/tests/profile_normalize.py

import random, cProfile, pstats, time, argparse, sys
from backend.photon_algebra.rewriter import (
    normalize,
    clear_normalize_memo,
    get_cache_stats,
    DIAG,
)

OPS = ["⊕", "⊗", "⊖", "¬", "↔"]

def random_expr(depth=4):
    """Generate a random Photon expression tree up to a given depth."""
    if depth <= 0:
        return random.choice(["a", "b", "c", "d"])

    op = random.choice(OPS)
    if op == "¬":
        return {"op": "¬", "state": random_expr(depth - 1)}
    else:
        n = 2 if op != "⊕" else random.randint(2, 4)
        return {"op": op, "states": [random_expr(depth - 1) for _ in range(n)]}


def run_profile(n=2000, depth=6, cold=False, top=30, progress=False):
    exprs = [random_expr(depth) for _ in range(n)]

    if cold:
        clear_normalize_memo()
        try:
            DIAG.reset()
        except Exception:
            pass

    def workload():
        for i, e in enumerate(exprs, 1):
            normalize(e)
            if progress and i % 100 == 0:
                print(f"… processed {i}/{n}", file=sys.stderr)

    profiler = cProfile.Profile()
    t0 = time.time()
    profiler.enable()
    workload()
    profiler.disable()
    elapsed = time.time() - t0

    print(f"\n⏱ Profiled {n} normalizations in {elapsed:.3f}s "
          f"({n/elapsed:.1f} exprs/sec)")
    print("Cache stats:", get_cache_stats())
    try:
        print("Diag counts:", DIAG.to_dict())
    except Exception:
        pass

    print("\nTop functions by cumulative time:")
    pstats.Stats(profiler).sort_stats("cumtime").print_stats(top)
    print("\nTop functions by per-call time:")
    pstats.Stats(profiler).sort_stats("tottime").print_stats(top)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2000, help="number of expressions")
    ap.add_argument("--depth", type=int, default=6, help="random tree depth")
    ap.add_argument("--cold", action="store_true", help="clear caches before run")
    ap.add_argument("--top", type=int, default=30, help="rows to show")
    ap.add_argument("--progress", action="store_true", help="print progress every 100 exprs")
    args = ap.parse_args()
    run_profile(n=args.n, depth=args.depth, cold=args.cold, top=args.top, progress=args.progress)