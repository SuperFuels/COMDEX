import os

# Best-effort: reduce numerical jitter from threaded BLAS/OpenMP reductions.
# (Must be set before heavy numeric work; pytest loads conftest early.)
for k in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(k, "1")
