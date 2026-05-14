import json, os, random, subprocess
from backend.photon_algebra.rewriter import normalize as py_norm

SEED = int(os.environ.get("SEED", "0"))
N = int(os.environ.get("N", "5000"))

def lean_norm(expr):
    p = subprocess.run(
        ["lake", "exe", "photon_algebra_audit"],
        input=(json.dumps(expr, ensure_ascii=False) + "\n").encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        cwd="backend/modules/lean/workspace",
    )
    return json.loads(p.stdout.decode("utf-8"))

def gen_expr(rng):
    # generate Photon ASTs in your JSON shape
    return {"op":"⊕","states":["a", {"op":"¬","state":"a"}]}  # replace with real generator

def test_python_matches_lean():
    rng = random.Random(SEED)
    for _ in range(N):
        e = gen_expr(rng)
        assert py_norm(e) == lean_norm(e)