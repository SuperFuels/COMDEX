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

## Refuelling to 3200 digits and extension to order 210

The persistent state format now supports atomic gzip compression, including
hash verification and resume checks.  This was required because the full
3200-digit triangular factor contains tens of thousands of rigorous interval
entries.

A fresh 3200-digit rebuild certified every Schur complement through order
210.  Direct determinant checkpoints were completed at orders 25, 50, 75,
100, 125, 150, 175, 200, and 210.  The final pivot was

`d_210 approximately 4.5303091e-933 > 0`.

The durable compressed state has hash

`dc7ea72e71b90490b6186d775e854d07d0f5691e596526b2d0fe86de0c40b7a3`,

and the block result has payload hash

`8102831bf806a4aafda2957080d2dae6127948a6e9322fa6c688d16b35d1557f`.

The complete rebuild took approximately 500 seconds locally.  High-precision
full-Li coefficient regeneration, rather than the resumed LDL transition, is
now the dominant scaling bottleneck.  The next engineering optimization
should therefore persist extendable Taylor and Stieltjes-series state in
addition to the Gram factorization.

The order-210 invariant analysis certifies 209 positive, strictly decreasing
transitions.  The last 30-stage midpoint window again marginally favours a
ratio proportional to `n^(-5/4)`, but neighbouring powers fit almost equally
well.  No power law has been promoted to a bound.  The invariant-analysis
payload hash is

`2110bd91b4b57d5083208fdd83f7fa5128664245bbbbb7bb95cb29d1d96910ff`.

The certified finite frontier is now order 210.  This remains neither an RH
proof nor evidence sufficient for RH; the universal positivity problem is
unchanged.

## Extendable Taylor--Stieltjes cache and order 240

`rh_frontier_li_coefficient_cache.py` removes the principal coefficient
rebuild bottleneck.  The cache preserves four interval series at fixed
precision:

* the regularized series for `(s-1) zeta(s)`;
* its formal logarithm;
* the Taylor coefficients of `log xi(1+t)`;
* the resulting full Li coefficients.

The saved stage-210 Li coefficients were used to bootstrap this cache without
recomputing all earlier Stieltjes constants.  The bootstrap inverts the exact
binomial transform

`lambda_n/n = sum_(k=1)^n binom(n-1,k-1) a_k`

to recover the completed-xi Taylor coefficients.  It then subtracts the
elementary and Gamma terms, exponentiates the remaining formal logarithm, and
performs direct Stieltjes overlap checks at degrees 1, 105, and 210.  All spot
checks passed.  Regression testing also compares a bootstrapped-and-extended
cache with an independently constructed coefficient sequence.

The cache produced coefficients 211--220 in approximately 39 seconds,
including the one-time bootstrap, and the rover certified stages 211--220 in
approximately 24 seconds.  A subsequent true extension computed only
coefficients 221--240 in approximately 69 seconds; the rover then certified
stages 221--240 in approximately 52 seconds without replaying the first 220
Gram transitions.

The order-240 pivot is

`d_240 approximately 4.8618720e-1085 > 0`.

The current hashes are:

* coefficient cache: `8a4aa0b84304f87815e5487e281ff0fe927b8fb6cf1651f03d504c1878962b86`;
* durable Gram state: `a8c9f92ea20edbfb669ba7ca5f85016cea431989a60e70ec9ef8dd03e98a2129`;
* stages 221--240 result: `cf7c75ebd30d7369c0eb0f653fbd24508eeb1bffa3c440d44a600b0a74fae8bc`;
* order-240 invariant analysis: `24685d89a7eb13e92c84e6f7f0961f5a25a364d26b66fe1aa3043fd206197d17`.

All 239 observed pivot transitions remain certified strictly decreasing.  The
last 30-stage heuristic window still marginally favours an `n^(-5/4)` ratio,
but the neighbouring powers remain competitive.  No numerical fit is treated
as a lower bound.

The certified finite frontier is now order 240.  This remains neither an RH
proof nor a disproof.

## Pascal-coordinate extraction from the Gram rover

The active strategy has shifted from extending the finite rover for its own
sake to extracting an exact invariant from its saved factorization.  Inspection
of the order-240 unit-lower LDL factor revealed a strong Pascal pattern:

`L_(n,n-j) approximately binom(n,j)`.

For example, in row 240 the first reverse entries are approximately

`1, 239.98016, 28675.22083, 2274706.759, ...`,

against the exact Pascal entries

`1, 240, 28680, 2276880, ...`.

The normalized defects

`[binom(n,j)-L_(n,n-j)] / binom(n-1,j-1)`

are positive in every sampled interval and drift slowly toward the scale of
`lambda_1`.  This is a finite numerical observation only; it is not being
promoted to an asymptotic theorem or lower bound.

The underlying coordinate change is nevertheless exact.  A new Lean theorem
proves, for every nonzero index `n` and every complex zero parameter `rho`,

`sum_(k=0)^n binom(n,k)(-1)^(n-k) liZeroMode(k,rho)
    = -(-rho^(-1))^n`.

Thus inverse Pascal transformation removes the binomial packaging of a Li
zero mode and exposes a signed reciprocal power of the zero.  This is a
universal finite algebraic identity and does not assume RH.

The companion exact-integer experiment applies the same inverse-Pascal
congruence to the abstract distance kernel

`G_(i,j)=lambda_i+lambda_j-lambda_|i-j|`.

Writing `mu_k` for formal reciprocal-zero power sums, it verified all 78
entries through order 12 against the closed coefficient formula

`(B G B^T)_(n,m) = (-1)^(n+m) sum_k
  [binom(n+m-k-1,n-1)+binom(n+m-k-1,m-1)] mu_k`,

where `B_(n,k)=(-1)^(n-k)binom(n,k)`.  The universal single-mode inversion is
Lean-checked; the displayed two-index kernel formula is currently an
exact-integer verified conjecture awaiting a general Lean combinatorial proof.

This explains why the rover's LDL factor resembles Pascal's triangle: the Li
sequence itself is a binomial transform of reciprocal-zero data.  The basic
binomial relation is known in the Keiper--Li literature, so no novelty claim is
made for that relation.  The useful research output is a sharper target:
replace the opaque shrinking Schur pivots by the inverse-Pascal quadratic form,
then search for a direct arithmetic or self-adjoint representation of that
form.  Such a representation would still have to prove positivity at every
finite order; the coordinate change alone is not progress toward a proof of
RH.

After applying the inverse Pascal matrix to the saved LDL factor, the reduced
factor is numerically close to a narrow lower-triangular Toeplitz matrix.  Its
first ten reverse diagonals suggested the provisional generating function
`(1-lambda_1 z) exp(-lambda_1 z^2)`.  Extrapolation across rows 80--240 was not
stable enough to support the proposed limiting constants, so this candidate
was immediately rejected from the theorem track.  It remains recorded only as
a possible source of better finite ansatzes.  This is the intended governance
behaviour: exact identities are promoted; attractive curve fits are attacked
and demoted when they do not stabilize.

Artifacts:

* `RiemannLab/Tasks/LiPascalTransform.lean`;
* `experiments/rh_frontier_pascal_structure.py`;
* `experiments/results/li_pascal_structure_v1.json`;
* `experiments/test_rh_frontier_pascal_structure.py`.

The Pascal-analysis payload SHA-256 is
`7c0ebae6cae87e7250fb2c2df8dfb951831777e53f64e6a6c61ddb1f334c252d`.

Verification completed with three focused regression tests and the complete
Lean build: 3,706 jobs passed, with no `sorry`, `admit`, or new axioms.

The next proof unit is fixed: prove the two-index inverse-Pascal kernel formula
in Lean and derive its finite quadratic form.  In parallel, decompose that
quadratic form into elementary/pole, Gamma, and prime contributions and test
whether the combined form admits an unconditional sum-of-squares, moment, or
self-adjoint-operator certificate.  The rover remains a falsifier and
conjecture miner, not the main proof engine.

## Universal Pascal--Toeplitz reduction

The first part of the next proof unit has now been completed in Lean.  Four
new universal results were added:

1. every nonzeroth inverse-Pascal row has total mass zero;
2. double summation against two zero-mass rows removes every separable term
   from a centered kernel;
3. inverse-Pascal congruence preserves the underlying finite quadratic form;
4. the complete two-index transform of a centered Li zero mode reduces exactly
   to a Toeplitz geometric kernel.

Writing

`q(rho)=1-rho^(-1)`,

the last theorem is

`sum_(i=0)^n sum_(j=0)^m B_(n,i) B_(m,j)
  [L_i(rho)+L_j(rho)-L_|i-j|(rho)]
 = sum_(i=0)^n sum_(j=0)^m B_(n,i) B_(m,j) q(rho)^|i-j|`,

for all positive `n,m` and every complex `rho`.  Here
`B_(n,i)=(-1)^(n-i)binom(n,i)`.  No critical-line or RH assumption occurs in
the proof.

This is stronger than a finite coefficient check: it identifies the exact
two-variable object that remains after changing coordinates.  All constant
and one-variable pieces cancel because the two Pascal rows have zero mass.
Only the discrete-distance kernel survives.

The finite quadratic-form theorem proves, for an arbitrary kernel `K`, that

`Q_(B K B^T)(c) = Q_K(B^T c)`.

Thus positivity is neither created nor lost by the coordinate change.  A
positive representation of the Toeplitz-side form would transfer directly to
the original Li--Gram form.

The surviving single-mode kernel also has the bivariate generating function

`sum_(n,m>=1) h_(n,m)(x) z^n w^m
 = x*z*w*(2+x*(z+w)) /
   [(1+z+w)(1+x*z)(1+x*w)]`,

where `x=rho^(-1)`.  A new exact-integer verifier checked the rational
coefficient recurrence for all `1024` pairs in the square
`1 <= n,m <= 32`.  The resulting payload hash is

`39ce330a7d67ef42fcff042b4a6a3e4d98e67a1c935be7499abf9099ff9c8f52`.

The rational generating function is not yet a universal Lean theorem, but it
provides a compact target for that proof and reproduces the earlier explicit
reciprocal-power coefficient formula.

The implementation commit is `97cc6cca`.  Four focused regression tests and
the full Lean build passed: 3,706 jobs, zero `sorry`, zero `admit`, and no new
axioms.

The next irreducible research unit is now narrower:

* formalize the rational generating-function identity in Lean;
* combine reflected modes `q` and `q^(-1)` and conjugate modes at the level of
  the Toeplitz quadratic form;
* transfer the resulting full-divisor form to the explicit prime/Gamma/pole
  side;
* search there for an unconditional positive operator or sum-of-squares
  representation.

This is structural frontier work, but it is not an RH proof.  The unresolved
step is still unconditional positivity after the contributions of the entire
zero divisor, or equivalently the complete arithmetic side, are assembled.

## Sparse three-lag off-critical quartet witness

The reflected/conjugate Toeplitz quartet can be reduced further.  Put

`q = 1-rho^(-1)` and `q+q^(-1)=a+ib`.

Its first three real Toeplitz lags are

`4`, `2a`, and `2(a^2-b^2)-4`.

Lean now evaluates the associated three-by-three determinant exactly as

`16*b^2*(a^2-b^2-4)`.

More importantly, determinant analysis is unnecessary.  The explicit vector

`c=(1,-a,1)`

satisfies the universal quadratic-form identity

`c^T T_3(a,b) c = -4*b^2`.

Consequently, every isolated reflected/conjugate quartet with `b != 0` is
certifiably not positive semidefinite in dimension three.  No eigenvalue
search, large Gram matrix, asymptotic limit, or height restriction is needed.

For `rho=beta+i*gamma`, Lean also verifies the coordinate reduction

`b = -gamma*(2*beta-1) / (X^2+C^2)`,

where

`X=gamma^2+beta*(1-beta)` and `C=gamma*(2*beta-1)`.

The denominator is positive whenever `C != 0`.  Therefore, for every
nonreal point (`gamma != 0`), leaving the critical line
`beta=1/2` produces the explicit negative witness above.  On the critical
line `b=0`, the witness value is zero, consistently with the existing
rank-two cosine Gram representation.

High-precision synthetic controls at the first-zero ordinate behaved exactly
as predicted.  The critical case `beta=0.5` gave zero.  Perturbations
`beta=0.5001`, `0.51`, `0.55`, `0.60`, and `0.75` all gave negative
three-by-three certificates; for example,

`beta=0.5001: det_3 approximately -1.59e-15`,

`beta=0.51: det_3 approximately -1.59e-11`.

The implementation commit is `99ed96aa`.  Five focused regression tests and
the complete Lean build passed: 3,707 jobs, zero `sorry`, zero `admit`, and no
new axioms.  The numerical-control payload SHA--256 is

`49f6b8a5cc806a913a8847ca789dfd296a2a44f7fe9c61f0721b2533fbf047ee`.

This is a substantial detector improvement, but not an RH proof.  The full
zeta divisor is a sum of quartet kernels.  Positive contributions from other
zeros can mask the negative value of one isolated off-line quartet.  The next
hard target is therefore a spectral localization or amplifier polynomial that
preserves the explicit `-4*b^2` defect of a selected quartet while bounding
the contribution of the remaining divisor.  That localized quadratic form
must then be transferred to the prime/Gamma/pole side and controlled without
assuming RH.

## Damped Chebyshev spectral amplifier

The first localization attack has produced a concrete finite polynomial

`C_(a,r,M)(z)=(z^2-a*z+1)*(1-z)^(2r)*(1+z^(2M))`.

Its three factors have separate jobs.  The quadratic seed preserves the exact
off-critical defect.  The even power of `1-z` damps high zeros.  The sparse
last factor is a cleared Chebyshev/Fourier tuner.  Lean proves the exact
reciprocal-product identity

`C(z)C(z^(-1)) = (u-a)^2*(2-u)^(2r)*
                  (1+z^(2M))*(1+z^(-2M))`,

where `u=z+z^(-1)`.  Lean also proves that, whenever reciprocal and conjugate
coincide, this product is exactly the complex norm square `|C(z)|^2`.
Consequently every critical-line background contribution is nonnegative; the
amplifier does not manufacture a false negative on that locus.

An exhaustive finite search over `1<=r<=10` and `1<=M<=100`, using the first
30 critical zeros, selected `(r,M)=(10,33)`, of polynomial degree 88.  For a
synthetic quartet at the ordinate of the first zero, the target-to-background
ratios were approximately

* `52.5` at `beta=0.5001`;
* `4.05e5` at `beta=0.51`;
* `7.00e4` at `beta=0.55`.

Thus the finite net is negative even for a displacement of only `10^(-4)`
from the critical line.  The initial high-precision search payload has
SHA--256
`2b6417f02f0558d877dfd4461d3657947d040ea8b72176b8fa92ebc5e710d937`.

The decisive numerical upgrade replaces ordinary high precision by
python-flint/Arb ball arithmetic.  Arb encloses the consecutive first 30 zeta
zeros, including the thirtieth ordinate near `101.3178510057`, and certifies
strictly negative finite-net intervals in all three cases.  For
`beta=0.5001`, the certified finite net is approximately

`-3.5527523418606762e-60`.

The damping order gives a critical-line tail majorant proportional to
`gamma^(-40)`.  Combining that decay with the already checked local Jensen
model

`count([t,t+1]) <= A + (12/log(8/7))*log(t)`

produces an explicit parametric tail budget.  In the hardest `beta=0.5001`
case, the finite negative margin survives provided the Jensen intercept
corresponds to

`log(K) < 2.130769774891017e17`.

This extremely large allowance shows that the critical-line infinite tail is
no longer numerically delicate.  The Arb payload SHA--256 is
`240ce0e09c1f7d87d82135e1e4dbb9b037c3ee2332a592df2ca62a02951dc4e9`.

The implementation commit for the initial amplifier is `734a4145`.  The full
Lean build passed 3,708 jobs, with zero `sorry`, zero `admit`, and no new
axioms.  Two focused amplifier regressions passed.

The claim boundary remains strict.  The first 30-zero block is rigorously
enclosed, but the abstract Jensen intercept has not yet been reduced to an
explicit numeric upper bound inside Lean.  More fundamentally, an RH proof
must handle an arbitrary simultaneous collection of off-line quartets, not a
single selected quartet against critical-line background.  The next two proof
units are therefore fixed:

1. close the critical-line tail by explicitly bounding the existing Jensen
   constant and importing the Arb enclosure as a replayable certificate;
2. replace the single-quartet scenario by an extremal/localization theorem
   showing that, if any off-line zero exists, some amplifier in a controlled
   family retains a negative total contribution after every other quartet is
   included.

Only after the second item is proved and the localized form is transferred to
an unconditional prime/Gamma/pole inequality would this route become a proof
of RH.  At present it is a much sharper, rigorously tested detector and a
plausible proof architecture, not a proof or disproof.

## Exact isolation of every finite dominant off-line cluster

The single-synthetic-quartet restriction has now been removed at the finite
dominant-cluster level.  The new construction has three machine-checked
components.

First, for a target mode `t` and a finite set `S` of competitors, Lean defines
the normalized interpolation filter

`I_(t,S)(z) = product_(w in S) (z-w)/(t-w)`.

If `t` is not in `S`, then

`I_(t,S)(t)=1`,

whereas

`I_(t,S)(w)=0`

for every `w in S`.  The construction was instantiated directly on the
multiplicity-aware compact zeta divisor, proving that any selected compact
zeta mode can be preserved while every other mode in that compact divisor is
annihilated exactly.

Second, a real-coefficient conjugate-pair annihilator was introduced:

`A_S(u) = product_(v in S) (u-v)(u-conj(v))`.

It vanishes at every listed coordinate and its conjugate, and it satisfies

`A_S(conj(u)) = conj(A_S(u))`.

Thus the filter can remove an arbitrary finite collection containing both
critical and off-critical competitors without sacrificing the conjugation
structure required for critical-line positivity.  The corresponding filter
in the Toeplitz variable is obtained by substituting

`u=z+z^(-1)`.

Lean verifies that this pulled-back filter is reciprocal symmetric:

`A_S(z^(-1)+z)=A_S(z+z^(-1))`,

so reciprocal pairing produces the exact square of one localized amplitude.

Third, a four-channel quadrature theorem removes the remaining complex-phase
ambiguity.  Let `w != 0` be the localized target amplitude and let `b != 0` be
the target's transverse off-critical coordinate.  The four channels are

`w`, `i*b*w`, `(1+i*b)w`, and `(-1+i*b)w`.

Lean proves that at least one of their squared real parts is strictly positive.
Multiplication by the quartet prefactor `-4*b^2` therefore gives a strict
negative certificate in at least one channel.  Consequently, after any finite
conjugate-symmetric competitor cluster has been annihilated, a separated
off-critical target cannot hide in all four channels.

The remaining question was whether the modes capable of competing with an
expansive target actually form a finite cluster.  This has also been answered
in Lean.  For every complex `rho != 0`,

`|1-rho^(-1)|^2 =
 ((Re(rho)-1)^2+Im(rho)^2)/(Re(rho)^2+Im(rho)^2)`.

If `Re(rho)>=0`, `R>1`, and

`R <= |1-rho^(-1)|`,

then Lean derives the explicit height bound

`Im(rho)^2 <= 1/(R^2-1)`.

Every nontrivial zeta zero also satisfies `0<Re(rho)<1`; hence all zeros whose
Li ratio has norm at least `R` lie in the explicit compact ball

`|rho| <= sqrt(1+1/(R^2-1))`.

The previously verified discreteness of the zeta zero set then implies:

`{rho : nontrivial zeta zero and R <= |1-rho^(-1)|}`

is finite for every `R>1`.

Finally, Lean combines this with the verified logical normal form for RH
failure.  If RH is false, reflection supplies an actual expansive zero mode
`rho` with

`1 < |1-rho^(-1)|`.

Choosing

`R=(1+|1-rho^(-1)|)/2`

gives

`1<R<|1-rho^(-1)|`,

and the complete set of modes capable of competing at threshold `R` is
finite.  Therefore all equally or more expansive competitors can be collected
into one finite cluster and removed by the exact conjugate-pair annihilator.

This closes the following parts of the proposed contradiction architecture:

1. selection of an expansive target from the assumption that RH is false;
2. proof that the complete dominant competitor set is finite;
3. exact annihilation of every dominant critical or off-critical competitor;
4. preservation of reciprocal and conjugation symmetry;
5. a four-channel guarantee that the selected target retains a strict negative
   defect despite an arbitrary complex phase.

The implementation commit is `978669d1`.  The complete Lean build passed
3,710 jobs, with zero `sorry`, zero `admit`, and no new axioms.

The proof is not complete.  Two irreducible obligations remain.  The first is
to show quantitatively that the infinitely many subdominant modes, whose Li
ratios have norm strictly below `R`, are overwhelmed by powers of the selected
target after zero-counting and multiplicities are included.  The second is to
transfer the resulting full-divisor negative form to the prime/Gamma/pole side
and establish the unconditional nonnegativity inequality needed for a
contradiction.

No actual off-critical zeta zero has been found, and RH is not claimed proved
or disproved.  The advance is that the former ``all off-line zeros act at
once'' objection is now resolved for the entire finite dominant cluster.  The
frontier has moved to an infinite subdominant-tail theorem and the arithmetic
positivity theorem.

## Abstract domination of the complete subdominant family

The exponential-gap mechanism required for the infinite remainder is now
formalized in Lean.  Let a selected target have magnitude

`A*R^n`,

where `A>0` and `R>0`, and suppose a remainder is bounded by

`C*r^n`

with `0<=r<R`.  Lean proves

`C*(r/R)^n -> 0`

and consequently

`C*r^n < A*R^n`

for all sufficiently large `n`.  Therefore any remainder satisfying

`tail(n) <= C*r^n`

obeys

`-A*R^n + tail(n) < 0`

eventually.  The same conclusion is proved from the stronger two-sided bound

`|tail(n)| <= C*r^n`.

The result was also lifted from one preassembled tail to an arbitrary infinite
mode family.  Let `weight(i)>=0` be summable, let `rate(i)>=0`, and suppose

`rate(i)<=r<R`

for every remaining mode.  Lean proves the complete infinite-sum estimate

`sum_i weight(i)*rate(i)^n
 <= (sum_i weight(i))*r^n`.

It follows that the entire infinite family is eventually smaller than
`A*R^n`.  This is the exact abstract theorem needed after the finite dominant
cluster has been removed.

The implementation commit is `8a03db92`.  The complete Lean build passed
3,711 jobs, with no `sorry`, `admit`, or new axioms.

The remaining analytic instantiation is precise: construct the actual
multiplicity-weighted amplitudes of the localized zeta divisor, prove that
their static weights are summable using the damping factor and the verified
`O(log T)` local zero count, and prove the uniform rate bound below the chosen
threshold.  Once those hypotheses are connected, the new theorem supplies the
strictly negative full-divisor form automatically.

## Literature audit and novelty correction

A literature comparison was performed before promoting this architecture as
new RH mathematics.  Bombieri and Lagarias proved that Li's criterion follows
from general inequalities for arbitrary multisets of complex numbers and
related its arithmetic formula to the Guinand--Weil explicit formula.  Weil's
positivity statement asserts that RH is equivalent to positivity of the Weil
quadratic functional over an appropriate family of test functions.  Lagarias
also explicitly relates Li coefficients to values of this Weil functional.

Accordingly, the current spectral programme must be interpreted carefully.
The expansive-mode selection, finite annihilation, four-channel phase removal,
and abstract exponential domination constitute a detailed Lean-verified
realization of the negative-witness direction of a Li--Weil positivity
criterion.  They are valuable formal infrastructure and may provide useful
new detector constructions, but they have not yet been shown to exceed the
known Bombieri--Lagarias/Weil equivalence framework.

In particular, proving that the final prime/Gamma/pole quadratic form is
nonnegative for every required localized test function is not a routine last
step.  Weil positivity for the full admissible class is itself equivalent to
RH.  A genuine breakthrough must therefore identify additional arithmetic
structure making the AION amplifier family unconditionally positive for a
reason that does not assume, restate, or smuggle in RH.

This audit changes the strategic emphasis.  Completing the actual summable
tail remains worthwhile because it produces a fully checked bridge into the
Weil functional.  However, the decisive research target is now the discovery
of a strictly stronger prime-side identity, sum-of-squares decomposition,
positive operator, or monotonicity principle that proves positivity for the
localized amplifier family independently of the zero locations.

The existing 250-digit Arb place decomposition was re-audited over every
nonempty subset of the three arithmetic components through matrix order 30.
The first certified negative principal-minor orders were:

* elementary/pole/pi alone: order 2;
* archimedean Gamma alone: order 1;
* regularized finite place alone: order 21;
* elementary plus Gamma: order 1;
* elementary plus finite place: order 4;
* Gamma plus finite place: order 1.

Only the complete three-place combination remained positive through all 30
checked orders.  This rigorously rules out every naive termwise or two-place
positivity decomposition at those finite orders.  Any successful arithmetic
certificate must expose a genuinely global cancellation coupling the pole/pi,
Gamma, and prime contributions simultaneously.  This negative result is
strategically useful: it prevents further effort being spent on a local-place
sum-of-squares that certified data has already falsified.

## Actual zeta-tail reduction and stationary three-place kernel

The abstract subdominant-tail theorem has now been instantiated on the actual
type of nontrivial zeta zeros.  `LiZetaTailEnvelope.lean` proves that this type
is countable from the verified finite compact truncations and their exhaustion
theorem.  It defines the intrinsic Li spectral rate

\[
  r(\rho)=\left|1-\rho^{-1}\right|
\]

and weights every localized amplitude by the analytic vanishing multiplicity
of zeta.  Under `not RH`, the already-proved expansive-target theorem now
produces an actual target, a threshold strictly between one and the target
rate, and a finite dominant cluster.  For the complete subtype of actual zeros
below that threshold, Lean proves exponential domination by the target as soon
as the multiplicity-weighted localized amplitude is summable.

This is a real instantiation, but it deliberately does not hide the final
analytic input.  The remaining tail theorem is to prove summability for the
specific damped finite-cluster annihilator.  The damping factor is expected to
reduce this to the checked local zero-counting estimate, but that implication
has not yet been formalized.

A second reduction converts the nonstationary Li distance kernel into a
stationary problem.  For a sequence `a` with `a(0)=0`, define

\[
  \tau_0=a_1,
  \qquad
  \tau_k=\frac{a_{k-1}-2a_k+a_{k+1}}{2}\quad(k\geq1).
\]

`LiStationaryIncrement.lean` proves that the mixed first difference of

\[
  G_{ij}=a_i+a_j-a_{|i-j|}
\]

is exactly the Toeplitz kernel `tau_|i-j|`.  It also proves the converse finite
telescoping identity

\[
  G_{mn}=2\sum_{i<m}\sum_{j<n}\tau_{|i-j|}.
\]

Thus a positive stationary increment kernel reconstructs every Li
distance--Gram matrix through cumulative summation.  This reframes the global
three-place search as a trigonometric moment problem rather than an unrelated
positivity problem at every matrix size.

The first certified continuous test used the Fejer polynomial

\[
  F_N(\theta)=\tau_0+2\sum_{k=1}^{N}
    \left(1-\frac{k}{N+1}\right)\tau_k\cos(k\theta).
\]

At `N=30`, Arb evaluated the polynomial on 131,073 interval points and used a
rigorous derivative majorant to cover every point between them.  The completed
three-place polynomial is certified positive on the entire interval
`0 <= theta <= pi`, with global lower bound greater than

\[
  1.403646844\times10^{-4}.
\]

The elementary pole/pi component and the archimedean Gamma component each have
certified negative values, whereas the regularized finite-place component and
the completed combination pass this particular continuous test.  The evidence
is stored in `li_three_place_toeplitz_fejer_v1.json`, whose payload hash is
`66fcbe5f8d26ce25c9b3a819a46ce78995d356b835b45779d1b919e3c9b613c9`.

This finite continuum certificate is stronger than a point grid but remains a
necessary-condition experiment at one order.  It does not prove the full
infinite Fejer family, construct a positive representing measure, or establish
RH.  The genuine frontier target is now sharper: derive an unconditional
positive measure or positive operator for the completed stationary increment
kernel, using an identity in which the prime, Gamma, and pole/pi terms are
coupled before positivity is taken.

## Multiplicity transfer and global damped-divisor summability

The summability programme has now moved beyond the conditional actual-tail
interface.  Four additional Lean modules close the complete positive-height
analytic chain.

`XiZetaMultiplicity.lean` proves the germ-level factorization

\[
  \Xi(s)=s(s-1)\Gamma_{\mathbb R}(s)\zeta(s)
\]

throughout the open critical strip.  The elementary/Gamma factor is proved
analytic and nonzero there.  Consequently, at every nontrivial zero,

\[
  \operatorname{ord}_{\rho}\Xi
  =\operatorname{ord}_{\rho}\zeta.
\]

This closes a genuine interface mismatch: the Jensen theorem counts the xi
divisor, whereas the Li amplifier uses zeta multiplicities.

`SummableShellEnvelope.lean` proves a general summability engine.  If a
countable divisor has nonnegative shell mass bounded by `C(n+1)`, then

\[
  \sum_i \frac{m_i}{(\operatorname{shell}(i)+1)^4}<\infty.
\]

The proof partitions the complete countable family into its exact fibers and
compares the outer series with the convergent cubic p-series.

`ZetaJensenShells.lean` then performs the actual geometric specialization.
Every nontrivial zero with

\[
  T\leq\Im\rho<T+1
\]

lies in the radius-`7/2` Jensen disk centred at `2+iT`.  Each such zeta shell
is therefore finite and contained in the exact xi-divisor support.  Lean
transfers the analytic multiplicities pointwise and proves

\[
  \sum_{T\leq\Im\rho<T+1}m(\rho)
  \leq
  \frac{\log C_J+12\log T}{\log(8/7)}
\]

for `T>=2`.  This is further converted to one explicit linear bound

\[
  \sum_{n+2\leq\Im\rho<n+3}m(\rho)
  \leq C_{\mathrm{shell}}(n+1).
\]

Finally, `ZetaDampedSummability.lean` assembles all positive shells into one
dependent countable union.  Lean proves that every nontrivial zero with
`Im(rho)>=2` occurs in exactly one shell and that

\[
  \sum_{\substack{\zeta(\rho)=0\\ \Im\rho\geq2}}
    \frac{m(\rho)}{(\operatorname{shell}(\rho)+1)^4}<\infty.
\]

Thus the positive-height multiplicity-weighted divisor is now unconditionally
summable under fourth-power damping.  To obtain the complete two-sided actual
amplifier weight, the remaining connection work is limited to conjugation
transfer for multiplicity and the finite low-height block, followed by the
polynomial bound for the already-constructed finite annihilator.

The completed stationary-symbol experiment was also extended from order 30 to
order 80.  At 150-digit Arb precision, 524,289 interval points and a rigorous
derivative covering estimate certify

\[
  F_{80}(\theta) > 5.701501820\times10^{-5}
  \qquad(0\leq\theta\leq\pi).
\]

The raw minimum enclosure is approximately
`1.102775392e-4`, and the covering error leaves the stated positive global
lower bound.  The evidence payload is
`li_three_place_toeplitz_fejer_v2_order80.json`, with SHA-256
`2f534607ea16ff90f7465ed7823804e2e02a0fb2406b7461377a44a4e6585db7`.

This order-80 result remains one finite continuum certificate.  It does not
prove positivity for every order or produce a positive representing measure.
The universal three-place operator remains the genuine frontier problem.

## Complete two-sided localized-amplifier summability

The three connection obligations left by the positive-height result are now
closed in Lean.

`ZetaTwoSidedDampedSummability.lean` proves directly from

\[
  \Xi(1-s)=\Xi(s)
\]

that functional-equation reflection preserves the exact analytic order of
`Xi`, and hence the zeta multiplicity of every nontrivial zero.  Reflection
maps every zero of ordinate at most `-2` into one of the verified
positive-height shells.  The complete negative-height multiplicity divisor is
therefore a second summable copy of the positive-height divisor.

The same module proves that

\[
  \{\rho:\zeta(\rho)=0,\ 0<\Re\rho<1,\ |\Im\rho|<2\}
\]

is finite by placing it inside a compact disk.  Thus no asymptotic estimate is
needed for the central block.

`ZetaAmplifierSummability.lean` treats the actual finite spectral amplifier.
For

\[
  q(\rho)=1-\rho^{-1}
\]

and `|Im rho|>=2`, Lean proves the uniform bounds

\[
  |q(\rho)|\leq\frac32,\qquad
  |q(\rho)^{-1}|\leq\frac32,\qquad
  |q(\rho)+q(\rho)^{-1}|\leq3.
\]

Consequently every fixed finite conjugate-pair annihilator is uniformly
bounded on the high-zero divisor.  For the fourth-power damped amplifier

\[
  A(\rho)=
  \bigl(q^2-aq+1\bigr)(1-q)^4
  \bigl(1+q^{2M}\bigr)
  \prod_{v\in\mathcal C}
    (q+q^{-1}-v)(q+q^{-1}-\overline v),
\]

Lean obtains an explicit finite constant `C(C,a,M)` satisfying

\[
  |A(\rho)|\leq \frac{C(\mathcal C,a,M)}{|\rho|^4}.
\]

This estimate is compared shell-by-shell with the previously verified
fourth-power divisor envelope.  The positive tail, reflected negative tail,
and finite central block are then reindexed onto the actual nontrivial-zero
subtype and assembled into the global theorem

\[
  \sum_{\rho}
    m(\rho)|A(\rho)|<\infty.
\]

Finally, `not_rh_localizedZetaAmplifier_tail_dominated` inserts this concrete
summability result into the expansive-mode theorem.  Under `not RH`, for every
fixed finite competitor set and amplifier channel, the complete
multiplicity-weighted subdominant zeta tail is eventually strictly smaller
than the selected expansive target.  The infinite-tail masking problem for
this amplifier is therefore closed.

This completes the analytic negative-witness envelope; it does not prove RH.
The remaining frontier is the opposite-sign theorem: an unconditional
positive measure, positive operator, sum-of-squares identity, or comparable
global principle for the completed prime--Gamma--pole stationary kernel.  The
finite order-80 certificate is evidence for that search, not a replacement for
the universal theorem.

## Negative-channel assembly and the positive-operator interface

`LiWitnessAssembly.lean` now performs the final sign bookkeeping between the
four-channel detector and the complete actual zeta tail.  The four possible
target coefficients are represented by one function on `Fin 4`; Lean proves
that a nonzero transverse localized target has a channel coefficient `D<0`.
It then proves the exact implication

\[
  \operatorname{tail}_n<-D R^n
  \quad\Longrightarrow\quad
  D R^n+\operatorname{tail}_n<0.
\]

Combining this with the two-sided summability theorem gives an eventual
negative assembled form under `not RH`.  The theorem intentionally keeps one
normalization bridge visible: the selected algebraic channel coefficient must
still be identified with the selected target's literal Weil-test-function
contribution.  This is no longer an infinite-tail estimate, but it must be
proved before the result may be called a complete Weil negative witness.

`LiStationaryPositiveOperator.lean` establishes the complementary operator
interface.  For a finite nonnegative spectral measure

\[
  \tau_n=\sum_x w_x\cos(n\theta_x),\qquad w_x\geq0,
\]

every stationary Toeplitz quadratic form has the exact factorization

\[
  \sum_{i,j}c_i c_j\tau_{|i-j|}
  =\sum_x w_x\left[
    \left(\sum_i c_i\cos(i\theta_x)\right)^2+
    \left(\sum_i c_i\sin(i\theta_x)\right)^2
  \right]\geq0.
\]

Lean also joins this identity to the previously verified cumulative
reconstruction of the Li distance kernel.  A positive stationary operator for
the increment lags forces

\[
  \lambda_n\geq0\qquad\text{for every }n.
\]

This is a sufficient operator certificate, not a construction of the required
measure for the actual completed arithmetic lags.  Assuming such a certificate
without constructing it would merely repackage the unresolved positivity
problem.

The selected direction is consistent with current primary operator work:
Suzuki's 2026 screw-function framework constructs self-adjoint localized Weil
operators without assuming RH but leaves the decisive limiting spectral
statement conjectural, while the finite Guinand--Weil dictionary and
archimedean-tail theorem give exact finite forms and a positive omitted
archimedean increment without proving the complete prime-coupled form positive.
See `arXiv:2606.09096` and `arXiv:2607.02828`.

The genuine frontier theorem is therefore now typed precisely: construct,
from primes, Gamma and pole terms together and without zero-location
assumptions, a positive spectral measure or operator whose moments are the
completed stationary Li increments.  Such a construction would make every Li
coefficient nonnegative through the checked SOS and reconstruction chain.  It
has not been obtained here.

## Laurent normalization and the exact Carathéodory target

`LiWeilLaurentNormalization.lean` closes the remaining finite algebraic
normalization ambiguity.  The quadratic seed, fourth-power damping,
oscillator, and complete finite conjugate-pair annihilator are now represented
by one finite Laurent polynomial

\[
  P(T)=
  (T^2-aT+1)(1-T)^4(1+T^{2M})
  \prod_{v\in\mathcal C}
  (T+T^{-1}-v)(T+T^{-1}-\overline v).
\]

Lean proves that evaluation at the literal zeta mode

\[
  q(\rho)=1-\rho^{-1}
\]

is exactly the localized amplitude used in the already-verified two-sided
summability and tail-domination theorem.  It also proves that the Laurent
autocorrelation is exactly the reciprocal-mode product

\[
  P(q)P(q^{-1}).
\]

Thus there is no longer a choice of normalization hidden between the finite
spectral detector and the global zeta-tail estimate.  What remains on this
side is analytic rather than algebraic: show that this finite Laurent test is
the literal member of the chosen admissible Weil test family, with the same
Fourier convention and completed prime--Gamma--pole normalization.

`LiCaratheodoryTransform.lean` isolates the positive-operator obligation even
more sharply.  For any real sequence `a` with `a(0)=0`, let

\[
  L_a(z)=\sum_{n\geq0}a(n+1)z^n,
  \qquad
  \tau_0=a(1),\qquad
  \tau_n=\frac{a(n-1)-2a(n)+a(n+1)}2\quad(n\geq1).
\]

Lean proves the exact formal-power-series identity

\[
  \tau_0+2\sum_{n\geq1}\tau_n z^n=(1-z)^2L_a(z).
\]

For the Li coefficients, the classical Li generating identity then predicts

\[
  \tau_0+2\sum_{n\geq1}\tau_n z^n
  =\frac{\Xi'}{\Xi}\!\left(\frac1{1-z}\right).
\]

This identifies the sought spectral measure with a Herglotz representation
of one explicit disk function.  The possible proof theorem is therefore:

\[
  \operatorname{Re}
  \frac{\Xi'}{\Xi}\!\left(\frac1{1-z}\right)\geq0
  \qquad(|z|<1),
\]

derived unconditionally from the combined prime, Gamma, and pole expression.
If established, Herglotz representation supplies the positive measure, the
checked Toeplitz SOS supplies every finite quadratic-form inequality, and the
checked reconstruction supplies every Li inequality.

This is a major reduction in specification, not an RH proof: positivity of
this completed disk function is itself an RH-equivalent frontier statement.
It may not be assumed, inferred from finitely many coefficients, or obtained
by proving the prime, Gamma, and pole pieces positive separately.  A successful
next step must expose a new global cancellation or positive realization of
their combined expression.

## Universal-kernel correction and exact arithmetic disk ledger

The positive-operator target has been corrected in
`LiUniversalPositiveKernel.lean`.  The earlier finite atomic measure is a
valid source of finite sum-of-squares certificates, but finite atomicity is
not an appropriate universal requirement for the actual Li kernel.  A finite
atomic cosine sequence is quasiperiodic, whereas the expected stationary Li
increments have non-atomic asymptotic behaviour.  The research target is now
defined directly as positivity of every finite Toeplitz compression:

\[
  \sum_{i,j}c_i c_j\tau_{|n_i-n_j|}\geq0
\]

for every finite choice of real coefficients and positions.  Lean proves
that this universal condition reconstructs every Li inequality.  It also
proves that a finite atomic certificate implies the universal condition, so
the previous finite experiments remain valid tests without being mistaken
for the required infinite representation.

`CompletedXiLogDerivative.lean` supplies the exact arithmetic normalization
on the absolute-convergence half-plane.  For `Re(s)>1`, Lean proves

\[
  \frac{\Xi'}{\Xi}(s)
   =\frac1s+\frac1{s-1}
    +\frac{\Gamma_{\mathbb R}'}{\Gamma_{\mathbb R}}(s)
    -\sum_{n\geq1}\frac{\Lambda(n)}{n^s}.
\]

The proof is germ-level: the entire xi factorization is established on a
neighborhood, differentiated there, and then joined to Mathlib's verified
von Mangoldt logarithmic-derivative theorem.  This rules out a hidden
normalization or sign choice in the proposed operator.

The same module pulls this identity back through the Li map

\[
  s=\frac1{1-z},\qquad
  \operatorname{Re}s=
  \frac{1-\operatorname{Re}z}
       {(1-\operatorname{Re}z)^2+(\operatorname{Im}z)^2}.
\]

It proves that the completed disk function equals the prime--Gamma--pole
ledger wherever the mapped point has real part greater than one.  This also
exposes the exact continuation obstruction: the prime Dirichlet series only
controls a proper subregion of the Li disk, while Herglotz positivity is
required on the complete disk, corresponding to `Re(s)>1/2`.

Two tempting but invalid routes are therefore removed:

1. a finite atomic measure cannot be imposed as the definition of the final
   operator;
2. the prime term cannot be made positive independently, because it occurs
   with the opposite sign in the completed ledger.

The remaining possible breakthrough must construct the full Toeplitz
quadratic form after the pole, Gamma, and prime terms have already been
combined, and must continue it from the absolute-convergence subdisk to the
whole Li disk without assuming zero-freeness.  That continuation-plus-global-
cancellation theorem remains open and is RH-level work; it is not supplied by
the identities above.

## Minimal Fejer-prefix target and arithmetic dominance

`LiPrefixEnergy.lean` audits the strength of the proposed universal operator.
For every normalized real sequence `a(0)=0`, Lean now proves the exact
telescoping identity

\[
  a(n)=\sum_{0\leq i,j<n}\tau_{|i-j|},
\]

where `tau` is the stationary second-difference sequence.  Thus termwise Li
positivity requires only the nested all-ones prefix forms, not every Toeplitz
quadratic form.  In a spectral representation these are precisely the Fejer
sum-of-squares tests

\[
  \left|\sum_{j=0}^{n-1}e^{ij\theta}\right|^2.
\]

Lean also verifies that universal Toeplitz positivity is strictly stronger
for general sequences: the normalized nonnegative sequence

\[
  a(0)=0,\qquad a(1)=1,\qquad a(2)=10,\qquad a(n)=0\ (n\geq3)
\]

has a negative two-point stationary quadratic form.  The universal operator
remains a valid sufficient route for zeta, but it is no longer treated as the
minimal theorem that must be proved.

This refinement agrees with Lagarias's primary Li--Weil analysis, which
identifies each Li coefficient with one Weil test and gives the arithmetic
decomposition

\[
  \lambda_n=S_\infty(n)-S_f(n)+1.
\]

See Jeffrey C. Lagarias, *Li Coefficients for Automorphic L-Functions*,
arXiv:math/0404394, especially equations (1.4)--(1.11) and Sections 3--4.

`LiArithmeticDominance.lean` encodes the resulting weakest arithmetic target.
For any exact ledger

\[
  a(n)=A(n)-F(n)+P(n),
\]

Lean proves the equivalences

\[
  F(n)\leq A(n)+P(n)\ \text{for every }n
  \quad\Longleftrightarrow\quad
  a(n)\geq0\ \text{for every }n
  \quad\Longleftrightarrow\quad
  \text{every prefix energy is nonnegative}.
\]

It also proves that a failure of dominance at one index gives an immediate
finite negative prefix certificate.  After instantiating the ledger for the
Riemann xi function, the frontier theorem is therefore exactly

\[
  S_f(n)\leq S_\infty(n)+1\qquad(n\geq1).
\]

This is a smaller and more accurate target than construction of an arbitrary
positive operator.  It is nevertheless still RH-equivalent after the
classical Li/Weil identification is installed.  The next nonclassical task is
to find a new uniform cancellation estimate for the signed finite-place term
strong enough to prove this inequality for every index; finite computations
or the unconditional leading asymptotic alone cannot supply it.

`RiemannLiSequence.lean` now attaches the minimal programme to an actual
completed-xi sequence.  It defines

\[
  G(z)=\frac{1}{(1-z)^2}
       \frac{\Xi'}{\Xi}\!\left(\frac1{1-z}\right)
\]

and takes the real Taylor coefficients of `G` at the origin, with
`lambda(0)=0`, as the derivative-normalized Riemann Li sequence.  Lean proves
that every one of these coefficients is exactly its corresponding stationary
Fejer-prefix energy and that positivity of the derivative-defined sequence is
equivalent to positivity of all those prefix energies.

This removes the final generic-sequence ambiguity.  Two classical analytic
identifications are still deliberately not asserted: equality of these Taylor
coefficients with the symmetrically truncated multiplicity-weighted zero sum,
and instantiation of the abstract arithmetic ledger by the literal Riemann
archimedean, finite-prime, and pole terms.  Those are the next formal bridge.
After it is installed, the only nonclassical statement remaining in this
route is the all-index dominance inequality above.

## Literal Riemann ledger and exact zero-sum interface

The abstract decomposition has now been instantiated on the actual
Taylor-defined completed-xi sequence.  `RiemannLiArithmeticLedger.lean`
constructs three analytic Li-disk functions: the elementary pole term, the
completed Gamma term, and the analytically continued finite-prime residual.
Lean proves the exact function identity

\[
  G(z)=G_\infty(z)-G_f(z)+\frac{1}{1-z}.
\]

On the portion of the disk mapped to \(\Re(s)>1\), the residual is proved to
be literally

\[
  G_f(z)=\frac{1}{(1-z)^2}
  \left(\sum_{m\geq1}\frac{\Lambda(m)}{m^s}-\frac{1}{s-1}\right),
  \qquad s=\frac{1}{1-z}.
\]

Thus the prime term is not introduced as an unnamed sequence or an assumed
ledger.  It is the analytic continuation of the regularized von Mangoldt
series.  Taking checked Taylor coefficients gives

\[
  \lambda_n=S_\infty(n)-S_f(n)+
  \begin{cases}0,&n=0,\\1,&n\geq1.\end{cases}
\]

Lean instantiates `LiArithmeticDecomposition` with these literal sequences and
proves

\[
  \bigl(\forall n,\ S_f(n)\leq S_\infty(n)+1\bigr)
  \quad\Longleftrightarrow\quad
  \bigl(\forall n,\ \lambda_n\geq0\bigr),
\]

with the normalized zeroth row handled separately.  A strict failure at one
index yields a finite negative Fejer-prefix certificate.

`RiemannLiZeroSumBridge.lean` now places the other classical representation on
the same compact multiplicity-aware zeta divisor used by the explicit-formula
programme.  For cutoff \(T\), it defines

\[
  \lambda_{n,T}=\sum_{\rho\in Z_T}
  m(\rho)\left[1-\left(1-\frac1\rho\right)^n\right],
\]

and proves that every stored divisor weight is exactly the analytic
multiplicity of zeta.  The zeroth row converges unconditionally, and the exact
remaining classical theorem is now named `RiemannLiTaylorZeroSumBridge`:

\[
  \lambda_{n,T}\longrightarrow\lambda_n
  \qquad(T\to\infty)
\]

for every fixed \(n\).  Proving this requires the order-one Hadamard product
with its symmetric convergence convention; pinned Mathlib does not provide
that global factorization as a ready theorem.  It remains classical connection
work, not an RH-level insight.

The claim boundary is therefore exact.  The completed arithmetic ledger is
closed.  The global Taylor-to-zero-sum Hadamard bridge remains classical and
open.  The uniform dominance inequality remains the genuinely nonclassical
RH-level theorem; it has not been proved.

## Quadratic zeta-divisor summability for the genus-one product

The first analytic prerequisite for the global Hadamard bridge is now
machine-checked.  `ZetaQuadraticSummability.lean` strengthens the previously
available fourth-power tail control to the quadratic damping required by a
genus-one canonical product.

Starting from the verified logarithmic bound for the multiplicity in each
unit-height zero shell, Lean proves the explicit elementary estimate

\[
  \log(n+2)\leq 4\sqrt{n+1}
\]

and hence a square-root envelope for the multiplicity mass of the shell.  It
then compares the quadratically damped shell series with the convergent
\(3/2\)-series.  The resulting package proves summability for the complete
positive-height shell union, transports it to negative heights using the
functional-equation reflection, and absorbs the finite central block.  In
schematic form, the checked conclusion is the convergence strength

\[
  \sum_{\rho}\frac{m(\rho)}{|\rho|^2}<\infty
\]

expressed through the programme's positive-shell, reflected negative-shell,
and finite low-height divisor models.

This is exactly the tail estimate needed to construct the primary factors

\[
  E_1\!\left(\frac{s}{\rho}\right)
  =\left(1-\frac{s}{\rho}\right)e^{s/\rho}
\]

with locally uniform convergence.  It does not by itself identify the
resulting product with the completed zeta function.  The remaining classical
Hadamard work is now sharply separated into four steps:

1. construct the locally uniformly convergent genus-one product from the
   checked quadratic summability package;
2. prove that its divisor, including multiplicities, is the nontrivial zeta
   divisor;
3. identify the quotient with \(e^{A+Bs}\) using the order-one growth of the
   completed xi function; and
4. differentiate the product and prove the symmetric truncation limit
   \(\lambda_{n,T}\to\lambda_n\) for every fixed \(n\).

All four remaining steps are established classical complex analysis.  The
separate all-index arithmetic inequality

\[
  S_f(n)\leq S_\infty(n)+1\qquad(n\geq1)
\]

is still the RH-equivalent breakthrough target.  Neither that inequality nor
RH has been proved.

## Verified genus-one primary factor

The local analytic component of the global Hadamard product is now closed in
`ZetaGenusOneCanonicalFactor.lean`.  The programme defines the literal
genus-one factor

\[
  E_{1,\rho}(z)=\left(1-\frac z\rho\right)e^{z/\rho}
\]

and Lean proves that it is entire, equals one at the origin, and, for
\(\rho\ne0\), vanishes exactly at \(z=\rho\).  Its derivative and logarithmic
derivative are checked exactly:

\[
  E_{1,\rho}'(z)
  =-\frac{z}{\rho^2}e^{z/\rho},
  \qquad
  \frac{E_{1,\rho}'(z)}{E_{1,\rho}(z)}
  =\frac1\rho+\frac1{z-\rho}.
\]

Most importantly, cancellation of the linear exponential term is formalized
as the uniform quadratic estimate

\[
  \left|E_{1,\rho}(z)-1\right|
  \leq 3\left|\frac z\rho\right|^2
  \qquad\left(\left|\frac z\rho\right|\leq1\right).
\]

Together with the preceding quadratic zeta-divisor summability theorem, this
is the exact Weierstrass majorant needed on every compact disk.  The remaining
global connection is no longer missing local factor analysis: it must expand
each zero according to its analytic multiplicity, apply Mathlib's uniform
infinite-product theorem to the two shell tails, attach the finite central
product, and then identify the resulting entire product with \(\Xi\) up to an
exponential linear factor.  Only after that identification may the product be
differentiated to close the symmetric Li zero-sum limit.

This remains established classical complex analysis.  It does not prove the
all-index arithmetic dominance inequality and does not prove RH.

## Literal multiplicity-expanded zeta divisor

The shellwise convergence model has now been converted into the literal
factor index required by the Hadamard product.  For each zero in the positive
tail, Lean introduces a finite fibre

\[
  \operatorname{Fin}(m(\rho)),
\]

so that the zero occurs once for every unit of its verified analytic
multiplicity.  The same construction is made for the reflected negative tail
and for the finite central block.

The checked shell estimates are then transported through these finite fibres.
Lean proves summability of the multiplicity-expanded quadratic shell weights,
identifies the actual complex point carried by every factor copy, proves that
none of those points is zero, and derives the literal inverse-square results

\[
  \sum_{j\in I_+}\frac1{|\rho_j|^2}<\infty,
  \qquad
  \sum_{j\in I_-}\frac1{|\rho_j|^2}<\infty.
\]

The multiplicity-expanded low-height index is proved finite, so its canonical
factor contribution is a finite product.  Consequently the next product
theorem no longer needs to reason indirectly through aggregate shell masses:
it can be stated directly over one canonical factor per multiplicity copy.

The remaining classical assembly is to apply the quadratic primary-factor
bound on compact disks, construct both tail products, multiply by the finite
central product, and identify the resulting entire function with the
completed xi function up to \(e^{A+Bs}\).  The RH-equivalent arithmetic
dominance inequality remains separate and unproved.

## Global entire genus-one canonical product

The canonical product has now been constructed, rather than merely specified
as a future obligation.  The local primary-factor estimate was strengthened
to the global bound

\[
  \left|E_1(w)-1\right|
  \leq 2|w|^2e^{|w|},
\]

which removes the need to discard finitely many factors when working on a
fixed compact disk.  A generic Lean theorem now proves uniform
multipliability on every closed disk for any nonzero divisor bounded away
from the origin and satisfying inverse-square summability.

Instantiating this theorem with the literal multiplicity-expanded zeta
divisor gives uniform products for both infinite tails on every closed disk.
Compact containment then promotes these results to locally uniform
convergence across the whole complex plane.  The two actual tail functions

\[
  P_+(z)=\prod_{j\in I_+}E_1(z/\rho_j),
  \qquad
  P_-(z)=\prod_{j\in I_-}E_1(z/\rho_j)
\]

are defined by convergent `tprod`s and proved entire using the locally uniform
limit theorem.  The finite central product \(P_0\) is also defined with one
factor per unit of analytic multiplicity.  Lean therefore constructs the
complete function

\[
  P(z)=P_+(z)P_-(z)P_0(z),
\]

proves that it is entire, and verifies the normalization

\[
  P(0)=1.
\]

This closes construction and analytic convergence of the full
multiplicity-aware genus-one product.  What remains in the classical
Hadamard bridge is the global divisor-identification theorem: prove that
\(P\) and \(\Xi\) have precisely the same zeros with the same analytic orders,
then use the checked order-one growth to show

\[
  \Xi(z)/P(z)=e^{A+Bz}.
\]

Differentiating that identity and matching the prescribed symmetric
truncations will close \(\lambda_{n,T}\to\lambda_n\).  None of these classical
connections proves the separate RH-equivalent arithmetic dominance
inequality, which remains open.

## Exact zero-set identification and exclusion of phantom zeros

The first half of divisor identification is now complete.  A new generic
nonvanishing theorem combines pointwise absolute summability of
\(E_1(z/\rho)-1\) with Mathlib's nonzero infinite-product criterion.  It
proves

\[
  \prod_j E_1(z/\rho_j)=0
  \quad\Longleftrightarrow\quad
  \rho_j=z\text{ for at least one }j.
\]

Thus locally uniform convergence cannot introduce a phantom zero.  This
theorem is instantiated separately on both infinite tails.  The analogous
finite-product statement is proved for the central block, and the three
results are combined into an exact zero ledger for the assembled product.

Lean also proves that every nontrivial zeta zero has strictly positive natural
analytic multiplicity.  Using the verified shell coverage, reflection, and
the central height band, it constructs an actual multiplicity-indexed factor
copy for every nontrivial zero.  Conversely, every factor point is already
certified as a nontrivial zeta zero.  The resulting checked theorem is

\[
  P(z)=0
  \quad\Longleftrightarrow\quad
  z\text{ is a nontrivial zero of }\zeta.
\]

Finally, every individual primary factor is proved to have analytic order
exactly one at its own zero.  The remaining divisor refinement is to isolate
the finitely many equal factor copies at a selected zero, prove the complementary
infinite product is locally nonvanishing, and sum these simple orders.  That
will establish equality of analytic multiplicities between \(P\) and \(\Xi\).

After multiplicity equality, the remaining Hadamard steps are the order-one
zero-free quotient theorem, determination of the exponential-linear factor,
and the symmetric Li truncation limit.  RH and the all-index arithmetic
dominance inequality remain unproved.

## Exact canonical-product multiplicities

The remaining divisor-identification theorem is now complete in
`ZetaGenusOneMultiplicity.lean`.  A generic inverse-square genus-one product
theorem was proved first: after every copy of a selected divisor point is
factored into a finite set, the complementary infinite product is locally
uniformly convergent, entire, and nonzero at that point.  The analytic order
of the full product is therefore exactly the number of selected copies.

This theorem was instantiated separately on the positive and reflected
negative multiplicity-expanded zeta tails.  Finite fibre finsets enumerate
all copies over one shell point, shell uniqueness rules out any missing or
duplicate base points, and their cardinalities are the verified xi/zeta
multiplicities.  A finite-product analytic-order theorem closes the central
height block.  The three regions are then assembled using additivity of
analytic order and the previously proved height separation.  Lean now checks

\[
  \operatorname{ord}_{\rho} P
  = \operatorname{ord}_{\rho}\Xi
\]

for every nontrivial zeta zero \(\rho\), where \(P\) is the complete
multiplicity-aware genus-one product.  Together with the earlier exact
zero-set theorem, this proves equality of the complete analytic divisors of
\(P\) and \(\Xi\), including multiplicity.

The full project build now passes 3,741 jobs.  The new file contains no
`sorry`, `admit`, new axioms, or unsafe assumptions.

The classical Hadamard bridge is consequently reduced to the zero-free
quotient stage:

1. extend \(\Xi/P\) across the common divisor and prove that it is entire and
   zero-free;
2. use the established order-one growth to prove
   \(\Xi(z)/P(z)=e^{A+Bz}\);
3. control \(A,B\) using normalization and functional symmetry; and
4. differentiate the factorization and identify the prescribed symmetric
   truncations, proving \(\lambda_{n,T}\to\lambda_n\).

These are classical connection steps.  The separate all-index inequality

\[
  S_f(n)\leq S_\infty(n)+1 \qquad (n\geq 1)
\]

remains the RH-equivalent breakthrough target and is not proved by the
divisor calculation.

## Non-circular certificate for the RH-level arithmetic inequality

The exact arithmetic target has now been audited for circularity. In the
current ledger, the finite-place quantity is defined by the completed
prime--Gamma--pole residual. Consequently, unfolding that residual in
\[
  S_f(n)\leq S_\infty(n)+1
\]
does not prove the inequality: it recovers precisely \(\lambda_n\geq0\).
Any argument based on that rearrangement has assumed the desired Li
inequality in another form.

`LiCoupledDominanceCertificate.lean` now records the minimal non-circular
proof object. It requires an independently constructed majorant \(M_n\)
satisfying
\[
  S_f(n)\leq M_n,
  \qquad
  M_n\leq S_\infty(n)+1
  \quad (n\geq1).
\]
Lean proves that such a certificate makes every Riemann Li coefficient
nonnegative. The intermediate \(M_n\) is deliberately not defined using a Li
coefficient; this is where a new prime-cancellation, energy, or monotonicity
theorem must enter.

A checked countermodel proves that an exact three-place ledger plus separate
nonnegativity of its archimedean, finite, and pole sequences is insufficient.
All three components in the model are nonnegative and the ledger is exact,
yet the represented Li-type sequence equals \(-1\) at every positive index
and dominance fails at index one. Quantitative coupling between the prime
and archimedean terms is therefore irreducible.

This is a strategic reduction and an anti-circularity theorem, not a proof of
RH. The surviving target is exact: construct \(M_n\) directly from the
prime-side expression and prove both inequalities uniformly for every
\(n\). Finite numerical positivity, a reconstructed residual, and separate
sign estimates do not meet this certificate.

## Literal prime-cutoff energy and certified-tail target

The abstract majorant requirement has now been pulled down to a literal
finite von Mangoldt calculation.  For the \(n\)-th Li test define

\[
 P_n(x)=\sum_{j=0}^{n-1}\binom{n}{j+1}\frac{x^j}{j!},
 \qquad
 C_n(x)=\sum_{j=0}^{n-1}\binom{n}{j+1}
                 \frac{x^{j+1}}{(j+1)!}.
\]

Here \(P_n\) is the associated-Laguerre weight appearing in the Li--Weil
prime formula, while \(C_n\) is its logarithmic compensation polynomial.
The coupled finite energy is

\[
 E_n(N)=S_\infty(n)+1+C_n(\log N)
   -\sum_{m\leq N}\frac{\Lambda(m)}{m}P_n(\log m).
\]

Keeping the compensation and prime sum together is essential: the two raw
terms diverge separately.  This agrees with the cutoff regularization in
[Lagarias's Li-coefficient treatment](https://www.numdam.org/item/AIF_2007__57_5_1689_0/).

`LiPrimeCutoffEnergy.lean` proves the finite moment interchange and the exact
prime-by-prime checkpoint equation

\[
 E_n(N+1)-E_n(N)
 =C_n(\log(N+1))-C_n(\log N)
  -\frac{\Lambda(N+1)}{N+1}P_n(\log(N+1)).
\]

It also proves the correct finite certification rule.  If a cutoff \(N_n\)
and independently proved error radius \(R_n\geq0\) satisfy

\[
 |\lambda_n-E_n(N_n)|\leq R_n,
 \qquad R_n\leq E_n(N_n),
\]

then \(\lambda_n\geq0\).  A uniform family of these certificates for all
\(n\) implies Riemann Li positivity.

Exploratory arithmetic stress tests rejected a tempting stronger invariant.
The individual checkpoint increments take both signs; for example, at
\(n=10\) there are both positive and negative increments below \(10^4\), and
intermediate cutoff energies can be negative even though the known finite Li
coefficient is positive.  Therefore neither monotonicity nor positivity at
every raw cutoff is a valid proof route.  The rover must carry a rigorous
tail-error budget, not merely inspect the current checkpoint sign.

The surviving RH-level obligation is now constructive and finite at each
index: derive a uniform analytic tail radius \(R_n(N)\) from prime-counting
information, choose \(N=N_n\), and prove
\(R_n(N_n)\leq E_n(N_n)\) for every \(n\).  This has not been proved; without
the uniform tail estimate the new recurrence is an instrument, not an RH
solution.

## Exact Abel decomposition of the prime-cutoff tail

The cutoff error has now been reduced to the Chebyshev remainder without any
zero-side assumption.  Define the smooth Li weight

\[
  w_n(x)=\frac{P_n(\log x)}{x}.
\]

Lean verifies the derivative identity \(C_n'(u)=P_n(u)\), its logarithmic
chain-rule form, all smoothness and finite-interval integrability conditions,
and the required integration-by-parts formula.  Abel summation is then
instantiated for the literal von Mangoldt sequence.  For \(1\leq N\leq M\),
the compensated tail

\[
 T_n(N,M)=
 \sum_{N<m\leq M}\frac{\Lambda(m)}mP_n(\log m)
 -\bigl(C_n(\log M)-C_n(\log N)\bigr)
\]

satisfies the exact checked identity

\[
\begin{aligned}
 T_n(N,M)
  ={}&w_n(M)\bigl(\psi(M)-M\bigr)
      -w_n(N)\bigl(\psi(N)-N\bigr)\\
    &-\left(
       \int_N^M w_n'(t)\psi(t)\,dt
       -\int_N^M w_n'(t)t\,dt
      \right).
\end{aligned}
\]

The stored rover energy is connected to this expression exactly:

\[
 E_n(M)-E_n(N)=-T_n(N,M).
\]

Thus a tail budget can be derived solely from finite prime data and bounds on
\(\psi(x)-x\).  `LiPrimeTailAbel.lean` defines the resulting explicit radius
\(B_n(N,M)\), proves

\[
 |E_n(M)-E_n(N)|\leq B_n(N,M),
\]

and packages the final uniform certificate.  If one proves, for selected
\(N_n\) and \(R_n\),

\[
 B_n(N_n,M)\leq R_n\leq E_n(N_n)
 \qquad\text{for every }M\geq N_n,
\]

together with the classical convergence of the regularized cutoffs, then
Lean derives every Li inequality.

This exposes two distinct remaining obligations.  First, the classical
regularized-cutoff convergence must be connected to the Taylor-defined Li
coefficient; pinned Mathlib does not contain the required prime number
theorem.  Second, and fundamentally, the resulting radius must beat the
positive checkpoint margin uniformly for every \(n\).  Known unconditional
prime-number-theorem bounds can make the tail converge for each fixed
polynomial weight, but no checked argument currently proves this all-index
margin.  Establishing it would be the RH-level breakthrough, not a final
routine estimate.

## Prime-number-theorem envelope and the exact margin obstruction

The Abel ledger has now been compressed to a single remainder integral.
Lean proves

\[
 \int_N^M w_n'(t)\psi(t)\,dt-
 \int_N^M w_n'(t)t\,dt
 =\int_N^M w_n'(t)(\psi(t)-t)\,dt.
\]

Consequently, any independently established pointwise envelope

\[
 |\psi(x)-x|\leq H(x)
\]

produces the checked cutoff-oscillation estimate

\[
 |E_n(M)-E_n(N)|\leq
 |w_n(M)|H(M)+|w_n(N)|H(N)
 +\int_N^M |w_n'(t)|H(t)\,dt.
\]

This is a reusable interface: the formal Li machinery no longer depends on
the particular proof or constants used for the prime-number theorem.

The elementary Chebyshev estimate available in the pinned Mathlib version
gives the linear envelope

\[
 H_0(x)=(\log 4+5)x.
\]

Lean proves that this estimate is quantitatively inadequate already for the
first Li weight:

\[
 |w_1(x)|H_0(x)=\log 4+5.
\]

The boundary contribution therefore does not tend to zero.  This is a
formal obstruction to using the library's elementary bound in the absolute
tail method, rather than merely a failed numerical experiment.

An explicit de la Vall\'ee Poussin--type envelope has also been installed:

\[
 H_{\mathrm{PNT}}(x)=
 10x(\log x)^2
 \exp\!\left(-\frac45\sqrt{\log x}\right).
\]

The deep statement
\( |\psi(x)-x|\leq H_{\mathrm{PNT}}(x) \) for \(x\geq3\) is represented as
an explicit proposition, not as an axiom.  Assuming that proposition, Lean
derives the corresponding Li cutoff-tail bound.  Formalizing suitable
published explicit PNT estimates, such as those of
[Johnston and Yang](https://arxiv.org/abs/2204.01980), would therefore close
the classical fixed-\(n\) convergence input without altering the downstream
certificate architecture.

The decisive logical boundary has also been formalized.  For any real
sequence \(E(N)\to L\) with \(L>0\), Lean constructs a checkpoint \(N\) and
a nonnegative radius \(R\) such that

\[
 |E(M)-E(N)|\leq R\leq E(N)
 \qquad(M\geq N).
\]

Thus a sufficiently strong PNT bound supplies convergence, but the existence
of a positive all-index checkpoint margin still depends on the positivity of
the limiting Li coefficient.  Proving such margins uniformly without already
assuming \(\lambda_n>0\) is not a routine consequence of the PNT: it is the
RH-level content of this route.  The programme has therefore separated the
remaining work cleanly:

1. reconstruct an explicit PNT estimate in Lean to close the classical
   fixed-index tail convergence; and
2. discover an independent uniform cancellation or positivity theorem that
   proves the checkpoint margin for every \(n\).

No proof or disproof of RH is claimed.

## Source-faithful Johnston--Yang bridge

The external PNT input has been sharpened from a generic placeholder to the
literal statement of Johnston--Yang, Theorem 1.1:

\[
 |\psi(x)-x|\leq
 9.39x(\log x)^{1.515}
 \exp\!\left(-0.8274\sqrt{\log x}\right)
 \qquad(x\geq2).
\]

All four decimal constants are represented by exact rational numbers in
Lean.  The theorem remains a proposition rather than an axiom.  Lean now
proves that, on \(x\geq3\), this literal published envelope is bounded by the
slightly relaxed project envelope

\[
 10x(\log x)^2
 \exp\!\left(-\frac45\sqrt{\log x}\right).
\]

The comparison is fully checked: it uses \(\log x\geq\log3>1\), monotonicity
of real powers in the exponent, and the stronger exponential decay
\(0.8274>0.8\).  A direct theorem now carries the source-faithful
Johnston--Yang conclusion into the finite Li cutoff-error certificate.

This does not yet constitute a Lean proof of Johnston--Yang's theorem.  The
paper's proof depends on several substantial external inputs, including a
certified RH verification up to height \(3{,}000{,}175{,}332{,}800\), explicit
zero-free regions, explicit zero-density estimates, a truncated explicit
formula, and finite numerical interval checks.  Neither the required
certificates nor this complete dependency chain exists in the pinned
Mathlib environment.  Replacing the proposition by a theorem with no
assumptions therefore requires importing or reconstructing that full
22-page analytic and computational proof; treating the published result as
an axiom would violate the programme's verification policy.

The formal boundary is consequently exact:

* the published statement, constants, relaxed-envelope comparison, and
  downstream Li tail connection are checked;
* the analytic/computational proof of the published PNT statement remains a
  classical formalization project; and
* even completing it would establish fixed-index tail control, not the
  all-index positive Li margin that is equivalent to the unresolved RH
  content.

The margin boundary is now a checked equivalence rather than an informal
warning.  If a real cutoff sequence \(E(N)\) converges to \(L\), then

\[
 L>0
 \quad\Longleftrightarrow\quad
 \exists N,R\geq0\;\;
 \left(
   \forall M\geq N,\ |E(M)-E(N)|\leq R
 \right)
 \land R<E(N).
\]

The forward implication constructs \(R=L/2\) after entering an
\(L/4\)-neighbourhood of the limit.  The reverse implication passes the
uniform finite tail bound to the limit and uses the strict checkpoint
surplus.  Applied separately at every Li index, the desired strict margin is
therefore exactly Li positivity expressed in cutoff coordinates.  A PNT
estimate can prove convergence and quantify the approach; it cannot supply
the positive limiting sign without an additional idea.
