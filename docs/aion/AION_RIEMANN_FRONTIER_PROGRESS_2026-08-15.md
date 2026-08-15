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

## Distance-Gram reformulation and sensitivity gain

The failed scalar moment models have been replaced by a structurally natural
matrix criterion.  From the Li sequence, with `lambda_0 = 0`, define

`G_(i,j) = lambda_i + lambda_j - lambda_|i-j|`.

For one critical-line zero mode, write its unit-circle ratio as an angle
`theta`.  `LiDistanceGram.lean` proves the exact identity

`(1-cos x) + (1-cos y) - (1-cos(x-y))`

`= (1-cos x)(1-cos y) + sin x sin y`.

Consequently every finite quadratic form for one mode is exactly the sum of
two squares

`(sum_i c_i(1-cos x_i))^2 + (sum_i c_i sin x_i)^2 >= 0`.

Thus the proposed matrix is the correct Gram object under the critical-line
geometry.  Conversely, positivity of every finite matrix forces
`lambda_n >= 0` from its diagonal entries, so after the standard analytic
zero-sum passage this is an RH-equivalent matrix target rather than a merely
necessary numerical pattern.

`rh_frontier_li_distance_gram.py` constructs these matrices directly from
the Arb-certified full Li coefficients.  All leading principal minors through
order **100** are rigorously positive at 800-digit working precision.  This is
finite evidence only and does not prove the infinite matrix criterion.

The same test was attacked by adding one synthetic off-line quartet at
`gamma = 14.134725...` to the complete zeta Li background.  A negative leading
principal minor was rigorously found at the following much smaller matrix
orders:

| Synthetic beta | First negative Gram minor | First negative isolated quartet mode |
|---:|---:|---:|
| `0.51` | `11` | `444` |
| `0.55` | `9` | `89` |
| `0.60` | `8` | `89` |
| `0.75` | `7` | `88` |

The matrix therefore exposes off-line geometry far earlier than coefficient-
by-coefficient sign testing in these adversarial cases.  The injected points
are not asserted to be zeta zeros.  The preserved certified result has payload
SHA-256 `4c307cd07e8a61ee2d1b08dc87ce6dc40d8cde4622d26c2d8b6f6fb172138c78`.

The frontier target is now sharper: seek an unconditional prime-side or
operator construction of this distance-Gram matrix.  A proof that every
finite instance is positive semidefinite would force all Li coefficients
nonnegative, while a negative principal minor would supply a finite
countercertificate.  Candidate constructions must not assume unit-modulus
zero ratios, since that would assume RH in disguise.

## Literature identification and correction of novelty status

A literature audit identified the distance--Gram matrix exactly as the Weil
scalar product on the Li test-function basis.  This is Theorem 3.1 of
J. C. Lagarias, ``Li coefficients for automorphic L-functions'', Annales de
l'Institut Fourier 57 (2007), 1689--1740.  For

`G_n(s) = 1 - (1 - 1/s)^n`,

Lagarias proves

`<G_n,G_m>_W = lambda_n + lambda_(-m) - lambda_(n-m)`.

For the Riemann zeta function the coefficient symmetries reduce the real
positive-index matrix to the distance--Gram form tested here.  The same work
also proves that positive semidefiniteness of the Weil form on the full Li
class is equivalent to RH.  Therefore the matrix criterion itself is not a
new RH equivalence and must not be presented as one.

The original contributions of the present laboratory are limited to the Lean
formalization of the finite algebra and reflection defect, the certified
full-coefficient matrix calculation, and its quantified adversarial
sensitivity tests.  `LiWeilBasis.lean` now verifies the core finite identity

`G_n(rho) G_m(1-rho) = G_n(rho) + G_m(1-rho) - G_(n-m)(rho)`

for natural indices with `m <= n`.  This locks the matrix to its correct
classical provenance and prevents an established equivalence from being
mistaken for a proof mechanism.

## Certified obstruction to place-by-place positivity

The arithmetic formula splits each Li coefficient into elementary/pole,
archimedean Gamma, and regularized finite-place contributions.  Because the
centered matrix construction is linear, the full distance--Gram matrix splits
into the corresponding three matrices.

`rh_frontier_li_place_decomposition.py` computes this split directly from the
Taylor expansion of `log xi` with Arb ball arithmetic.  The following leading
principal minors are rigorously negative:

| Component | First certified negative leading minor |
|---|---:|
| Archimedean Gamma | `1` |
| Elementary pole and pi normalization | `2` |
| Regularized finite-place zeta contribution | `21` |
| Complete combined matrix | none through `30` |

Thus no proof can proceed by declaring each natural local-place matrix
positive semidefinite and summing them.  The positivity visible in the full
matrix depends on cancellation between individually indefinite components.
This is a negative but strategically decisive result: it eliminates the most
direct prime-by-prime/local-place Gram ansatz.

The preserved decomposition has payload SHA-256
`ef28cf3477f48d98b2749b64691e3a72cb9ae608fd943512b914f6db9c60ecda`.

The surviving frontier question is therefore not whether the known Weil
form exists, but whether its global archimedean--finite cancellation can be
represented by a new unconditional positive operator, flow, or paired-prime
identity.  Any proposed construction must reproduce the complete combined
form; positivity of isolated Euler factors or isolated archimedean terms is
now certified to be false for the natural decomposition.

## Governed incremental Gram rover

`rh_frontier_gram_rover.py` implements the proposed proof-carrying transition
system.  It maintains an interval-certified factorization

`G_N = L_N D_N L_N^T`

and extends it by one row and column.  The next diagonal entry of `D` is the
Schur complement

`d_(N+1) = G_(N+1,N+1) - g^T G_N^(-1) g`.

The rover has fail-closed traffic states:

* a strictly positive Arb interval extends the certificate;
* a strictly negative interval halts with the explicit vector
  `[-G_N^(-1)g, 1]` and its certified negative quadratic form;
* an interval containing zero triggers a complete rerun at doubled precision;
* direct-determinant checkpoints must overlap the product of the LDL pivots;
* every stage and checkpoint is joined into a SHA-256 evidence chain.

The first preserved run covered the unmodified full-Li matrix through order
`100`.  It began at 200 digits, encountered unresolved pivots at stages 34 and
60, and automatically refuelled to 400 and then 800 digits.  At 800 digits all
100 Schur complements were certified positive.  Direct determinant checks at
orders 25, 50, 75, and 100 were positive and overlapped the independently
assembled LDL determinants.  Total wall-clock time was approximately seven
seconds on the local machine.

The three synthetic control lanes halted as intended:

| Control lane | Halt stage | Negative witness verified |
|---|---:|---:|
| `beta = 0.51` | `11` | yes |
| `beta = 0.55` | `9` | yes |
| `beta = 0.75` | `7` | yes |

The preserved rover result has payload SHA-256
`ba21fe371c84243b01aaabae5466cedc24301e7eedd07570d1307c43d6a521f5`.
Regression tests cover the positive lane, adversarial halt certificate,
checkpoint agreement, and stage-hash continuity.

The invariant-mining diagnostic certified that every one of the 99 observed
pivot transitions was strictly decreasing.  Its best simple midpoint-only
tail fit was

`d_n / d_(n-1) approximately C / n^(3/2)`

over stages 71--100, with fitted `C approximately 0.0270` and relative spread
about 5.6 percent.  This is only a conjecture-generation signal: it is not a
certified lower bound, it has not been derived analytically, and extrapolating
it would not prove positivity.  It supplies a concrete pattern for the next
symbolic attack rather than an RH claim.

This establishes that the rover is fast enough for substantial finite
exploration and sensitive enough to detect the injected controls.  It does
not overcome the infinity barrier: successful travel through any finite
order is not an RH proof.  Its research purpose is to expose pivot structure
from which a uniform lower bound or inductive invariant might be conjectured,
attacked, and ultimately proved.

## Durable block continuation

`rh_frontier_gram_rover_block.py` adds atomic checkpoint persistence.  A saved
state contains the interval-certified lower-triangular factor, its Schur
pivots, the Li coefficient enclosures used to build it, the evidence-chain
head, checkpoint hashes, precision, and a hash of the complete state.  On
resume the coefficients are recomputed and required to overlap the cached
intervals before the factorization is extended.

The first durable state rebuilt the certified order-100 factorization at 800
digits and then resumed it in a separate process.  The resumed rover certified
orders 101--105 positive and saved a new checkpoint at order 105.  At order
106 the 800-digit interval was unresolved, so the rover stopped without
promoting that stage and preserved the last valid state.  The state hash is

`5c7647b60fd3b8ce1a9ed730518d5cc8ca5c1be8298288373c8d3ce1aa702db6`.

This demonstrates continuation rather than replay of the earlier matrix
factorization.  Precision promotion remains deliberately non-magical: an
800-digit interval state cannot be converted into a 1600-digit state without
recomputation.  After that refuelling rebuild, subsequent blocks can again
resume from the new higher-precision state.

## High-precision extension to order 190

The rover was refuelled by rebuilding at 1600 decimal digits.  The first run
certified the complete prefix through order 150, including direct determinant
checkpoints at orders 25, 50, 75, 100, 125, and 150.  Its stage-150 Schur
complement was approximately `1.04e-637` and remained strictly positive.

Two subsequent processes loaded the saved factorization rather than replaying
the earlier LDL transitions.  They extended the certificate first through
order 180 and then through order 190.  The order-190 pivot was approximately
`2.84e-833` and was strictly positive.  At order 191, 1600-digit arithmetic
produced an interval containing zero; the rover therefore stopped, rejected
the unresolved stage, and preserved order 190 as the last certified state.
The current durable state hash is

`85be8aa153b81649f7c4c29d5b1f26a772edd69bff3785a3220240619990fc5b`.

This raises the certified incremental frontier from 100 to 190.  It remains a
finite verification and is not evidence that all future pivots are positive.
Continuing past 190 requires a new higher-precision rebuild, expected at 3200
digits under the current doubling policy.

The invariant-stability analysis now covers 189 transitions.  Every observed
pivot is certified positive and every observed transition is certified
strictly decreasing.  Thirty-stage window fits place the best simple ratio
model between powers `n^(-5/4)` and `n^(-3/2)`; the final window marginally
prefers

`d_n / d_(n-1) approximately 0.00788 / n^(5/4)`.

The neighbouring `n^(-3/2)` fit is nearly as good, so no exponent has been
promoted to a conjectured inequality.  The analysis is being retained as a
symbolic-search target only.  Its payload SHA-256 is
`3c064ae81b883d9fff0d3622671a9c5c3dab7b30b50b976bde42a3f0bd7c627e`.
