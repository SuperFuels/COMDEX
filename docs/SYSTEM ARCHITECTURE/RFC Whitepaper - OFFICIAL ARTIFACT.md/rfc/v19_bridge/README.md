# v19_bridge (Context/Token Amortization)

Regenerate locks:
  mkdir -p backend/tests/locks
  python backend/tests/glyphos_wirepack_v19_benchmark.py | tee backend/tests/locks/v19_out.txt
  (cd backend/modules/lean/workspace && lake env lean SymaticsBridge/ContextTokenAmortization.lean)
  sha256sum backend/modules/lean/workspace/SymaticsBridge/ContextTokenAmortization.lean backend/tests/locks/v19_out.txt \
    | tee backend/tests/locks/v19_lock.sha256

Verify:
  pytest -q backend/tests/test_v19_locks.py
