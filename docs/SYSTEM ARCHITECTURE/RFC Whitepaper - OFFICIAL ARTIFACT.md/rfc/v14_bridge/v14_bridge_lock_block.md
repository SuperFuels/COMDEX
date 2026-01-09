## WirePack v14 bridge: DNF blowup vs canonical tree (Lean-checked)

**Lean theorem (Bridge/DNFBlowup):** There exists a monotone Boolean program family \(F(n)\) whose full distributive expansion into DNF has \(2^n\) terms, while the canonical operator-tree representation has \(1 + 4n\) nodes.

- \(\mathrm{dnfTerms}(F(n)) = 2^n\) (exponential)
- \(\mathrm{nodes}(F(n)) = 1 + 4n\) (linear)

**This is the formal bridge behind the v14 benchmark table**: any representation that must materialize the fully-distributed DNF (or an equivalent expanded instruction stream that enumerates the terms) is forced into exponential growth for this family, while the canonical tree stays linear.

### Repro (repo-local)
- Lean check (inside Lean workspace):
  - `lake env lean SymaticsBridge/DNFBlowup.lean`
- Benchmark:
  - `PYTHONPATH=. python backend/tests/glyphos_wirepack_v14_dnf_blowup_benchmark.py`

### Lock (SHA-256)
- `SymaticsBridge/DNFBlowup.lean` (content hash): **b8fb5eea0fae3b965a71be6fcc7d54df0f6109ece344af328ef8c8b9baec0d5c**
- `backend/tests/glyphos_wirepack_v14_dnf_blowup_benchmark.py` (content hash): **b72f4bc665b8ac7ad3d8c736096e807b5312bb7d920b06306405781431304cb2**

