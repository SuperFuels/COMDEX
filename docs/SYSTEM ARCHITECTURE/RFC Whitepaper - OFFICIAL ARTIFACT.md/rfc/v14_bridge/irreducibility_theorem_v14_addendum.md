# Addendum: WirePack v14 Bridge — DNF Blowup vs Canonical Tree (Lean-checked)

This addendum installs the missing “bridge” that makes the compression story *not just gzip*.

## Theorem (DNF blowup family)

Define a monotone Boolean formula family:

\[
F(n) = \bigwedge_{i=0}^{n-1} (x_i \lor y_i)
\]

Let `dnfTerms` count the number of conjunction-terms after full distributive expansion into DNF (monotone counting model):
- `dnfTerms(var)=1`, `dnfTerms(or)=+`, `dnfTerms(and)=*`.

Let `nodes` count syntactic nodes in the canonical operator tree.

**Lean-checked statement:**

- \(\mathrm{dnfTerms}(F(n)) = 2^n\) *(exponential)*
- \(\mathrm{nodes}(F(n)) = 1 + 4n\) *(linear)*

**Interpretation:** any representation that must materialize (or equivalently enumerate) the fully-distributed DNF is forced into exponential growth on this family, while the canonical tree remains linear.

## Repro (repo-local)

- Lean check (inside Lean workspace):
  - `lake env lean SymaticsBridge/DNFBlowup.lean`
- Benchmark:
  - `PYTHONPATH=. python backend/tests/glyphos_wirepack_v14_dnf_blowup_benchmark.py`

## Lock (SHA-256)

- `SymaticsBridge/DNFBlowup.lean`: **b8fb5eea0fae3b965a71be6fcc7d54df0f6109ece344af328ef8c8b9baec0d5c**
- `backend/tests/glyphos_wirepack_v14_dnf_blowup_benchmark.py`: **b72f4bc665b8ac7ad3d8c736096e807b5312bb7d920b06306405781431304cb2**
