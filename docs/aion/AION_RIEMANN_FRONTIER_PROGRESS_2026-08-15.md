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

## Certified full-coefficient computation

`rh_frontier_li_full_arb.py` now computes Li coefficients from the Taylor
expansion of the complete xi-function at `s=1`.  It uses Stieltjes constants
and Arb ball arithmetic rather than truncating a list of zeros, so every
reported interval encloses the corresponding full coefficient.  The
calculation uses the generating identity

`log xi(1/(1-z)) = log xi(1) + sum_(n>=1) lambda_n*z^n/n`.

The first **300** full Li coefficients have strictly positive certified
intervals.  The calculation was repeated at 400 and 500 decimal digits; all
corresponding intervals overlap and all remain strictly positive.  The
preserved 400-digit result has payload SHA-256
`812f43dfa783a211699ee7be0d6a43f0d31e3c47642297a46cab4222d224a6d9`.
This is a finite validation result and is not evidence sufficient to prove
RH.  Li's criterion requires every coefficient.

## First certified moment/Gram rejection

`rh_frontier_li_moment_search.py` tests the necessary Hankel positivity
condition for three natural positive-measure moment ansatzes.  Arb proves that
their order-two leading Hankel determinants are strictly negative:

| Candidate moment sequence | Certified determinant sign |
|---|---:|
| `lambda_(n+1)` | negative |
| `lambda_(n+1)/(n+1)` | negative |
| `lambda_(n+2)-lambda_(n+1)` | negative |

Thus none of these three sequences can be the moments of a positive measure,
and the corresponding simple Hankel-Gram strategies are rejected globally by
a finite certificate.  This does not rule out other Gram, norm, kernel, or
sum-of-squares representations.  The preserved rejection result has payload
SHA-256 `54195428c770be1122056bcc5c176d3dbddae54afcbcb1de6fae34ff9dde2f5b`.

The next search must therefore use structure beyond a scalar positive moment
sequence: a test-function Gram form, a matrix-valued moment problem, or a
prime-side sum-of-squares identity.  Candidates will continue to be required
to survive rigorous enclosures and injected off-line quartets before any Lean
formalization effort.

## Reflection-paired norm-square identity

`LiPairIdentity.lean` formalizes the exact algebraic structure that survives
the failed scalar moment ansatzes.  For the single-zero Li mode

`a_n(rho) = 1 - (1 - 1/rho)^n`,

Lean proves

`a_n(rho) + a_n(1-rho) = a_n(rho) * a_n(1-rho)`.

When `re(rho)=1/2`, reflection equals conjugation, and the right side becomes

`|a_n(rho)|^2 >= 0`.

This is a genuine checked sum-of-squares identity for each reflected pair,
but it is conditional on that pair already lying on the critical line.  It
therefore explains Li positivity under RH; it does not prove RH.  The new-idea
target is now precise: reproduce this norm-square structure from unconditional
prime-side or operator data without assuming `re(rho)=1/2`.  Any construction
that uses reflection-as-conjugation before establishing the critical-line
condition will be rejected as circular.
