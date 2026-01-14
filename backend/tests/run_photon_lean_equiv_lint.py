import json, subprocess, random
from backend.photon_algebra.rewriter import normalize as py_norm

SEED = 0
random.seed(SEED)

def lean_norm(expr_json):
    p = subprocess.run(
        ["lake", "exe", "photon_algebra_audit"],
        input=json.dumps(expr_json).encode(),
        stdout=subprocess.PIPE,
        check=True,
        cwd="backend/modules/lean/workspace",
    )
    return json.loads(p.stdout)

def test_equiv(N=500):
    for _ in range(N):
        e = random_expr()  # use your generator
        assert py_norm(e) == lean_norm(e)