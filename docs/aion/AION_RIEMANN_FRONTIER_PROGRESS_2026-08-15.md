# AION Riemann Frontier Programme — First Verified Experiment

**Date:** 15 August 2026  
**Track:** Genuine RH frontier research  
**RH proved or disproved:** no

## Formal counterexample normal form

`OffCriticalQuartet.lean` proves, without assuming that RH is false,

`not RH <-> exists rho, IsNontrivialZetaZero rho and 1/2 < re(rho)`.

Thus every possible failure of RH has a canonical representative on the
right-hand side of the critical strip.  Its reflection and conjugates form
the standard verified zero orbit.  The file also proves the exact algebraic
transition underlying Li's criterion:

`|1 - 1/rho| < 1 <-> 1/2 < re(rho)`,

`1 < |1 - 1/rho| <-> re(rho) < 1/2`.

Consequently a right-hand counterexample has a reflected zero carrying an
expansive Li mode.  These statements are established complex algebra and do
not constitute new evidence for or against RH.

## Adversarial Li-quartet sensitivity experiment

`rh_frontier_li_quartet.py` evaluates, using deterministic high-precision
decimal arithmetic, the isolated contribution

`sum_z (1 - (1 - 1/z)^n)`

over a hypothetical symmetry quartet at the ordinate of the first known zeta
zero.  The result is a detector calibration, not a claim that any hypothetical
off-line point is a zeta zero.

| Hypothetical real part | First negative isolated contribution |
|---:|---:|
| `0.50` | none through `n = 200000` |
| `0.51` | `n = 444` |
| `0.55` | `n = 89` |
| `0.60` | `n = 89` |
| `0.75` | `n = 88` |

The first-negative results agree exactly between 80- and 120-digit runs.  The
preserved 80-digit output has SHA-256 payload hash
`5e0c7cf1fa62144585bf6bf4b8c14e15e60919bf054f50e1cc33081c089e7f89`.

## Interpretation and next gate

The experiment confirms the expected mechanism: on the critical line the Li
ratio has modulus one, whereas an off-line quartet contains a mode of modulus
greater than one.  It does not locate an off-line zero and does not prove a
negative full Li coefficient, because the complete coefficient includes every
zero with the prescribed limiting convention.

The next frontier unit is to replace the isolated-quartet model with a
rigorously bounded full-coefficient experiment and search for a structural
Gram or sum-of-squares representation.  A successful result must apply to all
indices, not merely a finite verified range.  Numerical work remains a
falsification and conjecture-generation layer; theorem claims require Lean
verification.
