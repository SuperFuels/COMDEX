# backend/photon_algebra/tests/bench_normalize.py

import time
import random
from backend.photon_algebra.rewriter import normalize, get_cache_stats, DIAG

OPS = ["⊕", "⊗", "⊖", "¬", "↔"]

def random_expr(depth=4, atoms=("a", "b", "c", "d")):
    """Generate a random Photon expression tree up to a given depth."""
    if depth <= 0:
        return random.choice(atoms)

    op = random.choice(OPS)
    if op == "¬":
        return {"op": "¬", "state": random_expr(depth - 1, atoms)}
    else:
        n = 2 if op != "⊕" else random.randint(2, 4)
        return {"op": op, "states": [random_expr(depth - 1, atoms) for _ in range(n)]}


def test_benchmark_normalize():
    N = 5000
    exprs = [random_expr(5) for _ in range(N)]
    start = time.time()
    for e in exprs:
        normalize(e)
    elapsed = time.time() - start

    stats = get_cache_stats()
    print(f"\n⏱ Ran {N} normalizations in {elapsed:.3f}s "
          f"({N/elapsed:.1f} exprs/sec)")
    print("Cache stats:", stats)

    # Collect diagnostic counters
    try:
        diag_dump = DIAG.to_dict()
    except AttributeError:
        diag_dump = {k: getattr(DIAG, k) for k in dir(DIAG) if not k.startswith("_")}
    print("Diag counts:", diag_dump)