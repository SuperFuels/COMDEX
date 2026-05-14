# Lexicon v0 (Stage B / P11) — Token contract + canonical metrics

Status: READY-TO-LOCK (spec file)  
Maintainer: Tessaris AI  
Author: Kevin Robinson  
Last update: 2026-01-02 (Europe/Madrid)

## Scope
This document defines the **canonical** SIM lexicon v0 (“wave alphabet”) and the **canonical** metric definitions used by the Stage B harness (B0/B1) and downstream stages (P12/P13).  
All semantics here are **model-scoped** and **engineering-defined**.

---

## Token set v0

Each token is a named field in a Program state (or time-scheduled updates to that state).

### Core tokens
- **ω**: angular frequency (rad/s) or per-node frequency map `ω[i]` (when banked).
- **A**: drive amplitude (scalar or per-node amplitude map `A[i]`).
- **φ**: phase offset (rad), scalar or per-node.
- **p / parity**: parity bit or sign convention token (e.g., ±1); used for symmetry/handedness tagging.
- **m(x)**: spatial mask / envelope (windowed or localized shape), used to target regions/nodes.
- **τ**: time constant(s) (e.g., damping, filter windows, lock detectors).
- **env**: environment / exogenous field bundle (noise floor, global carrier, perturbations, budgets).

### Optional extension tokens (declared but non-blocking)
- **budget**: energy/work budget constraints (if enforced later).
- **topology**: adjacency / graph structure source tag (telemetry vs bootstrap), if included as a tokenized input.

---

## Program model (canonical)
A Program is an **audit-friendly**, time-indexed schedule of token assignments.

Minimum required semantics:
- Program execution MUST be deterministic given `(Program, seed, dt)`.
- Token updates MAY be piecewise-constant over time intervals.
- A Program MAY include a “gate” scalar and/or gate schedule (see below).

Recommended minimal structure (conceptual):
- `t`: current simulation time
- `state`: current token state (ω, A, φ, p, m(x), τ, env, …)
- `schedule`: a list of time-ranged assignments to `state`

This spec does not require a specific JSON schema; it requires the **token meanings** and the **metric meanings** below to be stable.

---

## Response channels (canonical)
SIM tests consume responses via these channels:

1) **Amplitude / phase / lock**
   - amplitude proxy (energy-like)
   - phase (or phase difference)
   - lock indicator (sustained synchronization / bounded drift)

2) **Routing success**
   - did the intended target respond more strongly than non-targets under the same drive?

3) **Geometry error**
   - discrepancy between expected adjacency / schedule effects and observed convergence or coupling metrics

---

## Canonical metrics (definitions)

### 1) Amplitude proxy (oscillator-bank canonical)
For a state `(x, v)` with target frequency `ω > 0`, define the frequency-normalized energy proxy:
\[
E(t) = x(t)^2 + \left(\frac{v(t)}{\omega}\right)^2
\]
Rationale: removes trivial ω-bias so selectivity is not an artifact of frequency scaling.

If a node bank exists, define per-node:
\[
E_i(t) = x_i(t)^2 + \left(\frac{v_i(t)}{\omega_i}\right)^2
\]

Time aggregation (canonical):
- Use tail-window mean (or median) after warmup:
\[
\overline{E_i} = \mathrm{mean}_{t \in \text{tail}} E_i(t)
\]

### 2) Selectivity (target vs others)
Given a target index `k` and a set of non-target indices `\mathcal{O}`:
\[
\mathrm{selectivity}(k) = \frac{\overline{E_k}}{\epsilon + \mathrm{mean}_{i \in \mathcal{O}} \overline{E_i}}
\]
- `ε` is a small stabilizer to avoid divide-by-zero in low-energy regimes.
- Passing behavior: selectivity SHOULD be high when addressing is correct.

### 3) Crosstalk (non-target activation)
Define:
\[
\mathrm{crosstalk}(k) = \frac{\mathrm{mean}_{i \in \mathcal{O}} \overline{E_i}}{\epsilon + \overline{E_k}}
\]
Passing behavior: crosstalk SHOULD be low in correct addressing.

### 4) Coupling / ΔC (engineered coupling signature)
Define a coupling score `C` as a monotone indicator of “connected response” between two loci (A,B).
Allowed canonical proxies (choose one per test and record it):
- **Phase-lock proxy**: `C = 1 - mean(|wrap(Δφ)|)/π`
- **Coherence proxy**: `C = |⟨e^{jΔφ}⟩|`
- **Response-transfer proxy**: `C = corr(y_A, y_B)` (post-warmup)

Then:
\[
\Delta C = C_{\text{match}} - C_{\text{mismatch}}
\]
Passing behavior: matched condition SHOULD exceed mismatch; ΔC SHOULD be positive and separated.

### 5) Lock and drift (phase-drift metric)
Define instantaneous phase difference:
\[
\Delta\phi(t) = \mathrm{wrap}(\phi_A(t) - \phi_B(t))
\]
Define drift over a tail window:
\[
\mathrm{drift} = \mathrm{mean}_{t\in\text{tail}} \left|\Delta\phi(t) - \mathrm{mean}_{\text{tail}}(\Delta\phi)\right|
\]
Lock criterion (canonical): sustained lock if drift stays below a fixed threshold for a fixed duration.

### 6) Energy (drive / work proxies)
Energy is model-scoped; canonical minimum:
- **drive energy**: \( W_{\text{drive}} = \sum_t \sum_x d(t,x)^2 \)
- **total energy** MAY include additional channels if defined (feedback, env, etc.)

### 7) Rigidity (optional)
Rigidity is a stability proxy describing sensitivity of metrics to small perturbations:
- Example: slope of response metric vs small noise or small parameter jitter (recorded as `d(metric)/dσ`).
Rigidity is optional for v0; if used, it MUST be explicitly defined in the test that uses it.

### 8) Mutual information (optional later)
`I(u; y)` is explicitly deferred in v0; if introduced later, it MUST be defined with:
- estimator type (discrete bins / kNN / gaussian)
- windowing
- seed averaging

---

## Ablation expectations (Stage B contract)
Stage B tests MUST enforce that removing critical tokens/gates breaks the intended signature.

### Ablation matrix (expected failures)
1) **Remove ω (wrong ω / ω ablation)**
   - A2 selectivity SHOULD collapse (target no longer uniquely excited)
   - crosstalk SHOULD increase
   - expected: `selectivity ↓`, `crosstalk ↑`

2) **Remove gate / gate ablation**
   - adjacency override effects SHOULD weaken
   - expected: coupling advantage due to gated mechanism shrinks
   - in A4-style tests: the “k_link advantage” SHOULD shrink under low gate

3) **Remove chirality match (chirality mismatch)**
   - A3.1 matched-vs-mismatched separation SHOULD collapse or invert
   - expected: `C_match` no longer significantly > `C_mismatch`; ΔC shrinks

4) **Remove topology schedule (topology schedule ablation)**
   - any time-dependent topology-driven effect SHOULD collapse to baseline
   - expected: routing or geometry-dependent improvements vanish (return to ungated / distance-decay behavior)

### What MUST remain invariant
- Seeds and deterministic schedules MUST be stable across runs for lock verification.
- Metric formulas in this document MUST not drift without a new version bump (Lexicon v1).

---

## Canonical repo references (informational)
- Lexicon implementation: `Glyph_Net_Browser/src/sim/lexicon.ts`
- Metrics implementation: `Glyph_Net_Browser/src/sim/metrics.ts`
- Stage B tests:  
  - `Glyph_Net_Browser/src/sim/tests/B0_lexicon_contract.test.ts`  
  - `Glyph_Net_Browser/src/sim/tests/B1_ablation_matrix.test.ts`

---

## Lock footer
Lock ID: P11-LEXICON-V0-2026-01-02  
Status: LOCK-READY  
Maintainer: Tessaris AI  
Author: Kevin Robinson.
