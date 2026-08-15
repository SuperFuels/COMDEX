# AION Riemann Programme - Mathematics Progress Update

**Date:** 15 August 2026  
**Authority:** Lean 4.24.0 kernel with pinned Mathlib v4.32.1  
**New RH mathematics claimed:** none

## Result

The previously identified critical-strip blocker has been closed as a formal
reconstruction of established mathematics. A new Lean module defines trivial
and nontrivial zeta zeros and proves:

1. every zeta zero with nonpositive real part is a negative-even trivial zero;
2. every nontrivial zero satisfies `0 < s.re`;
3. every nontrivial zero satisfies `s.re < 1`;
4. therefore every nontrivial zero lies in the open critical strip;
5. reflection `s -> 1 - s` preserves nontrivial zeros;
6. complex conjugation preserves nontrivial zeros;
7. the standard four-point symmetry orbit consists of nontrivial zeros; and
8. the local formulation is equivalent to Mathlib's `RiemannHypothesis`.

All nine theorems compile without `sorry`, `admit`, new axioms, or unsafe
assumptions. A second module adds five kernel-checked bridge and bound-structure
theorems for the selected Chebyshev route. The compact-divisor and finite
explicit-formula modules add fifteen further checked theorems. Together with
the earlier foundation, the laboratory now contains 49 kernel-checked research
theorems (52 declarations including the three baseline reproduction checks).

## Core mechanism of the left-half-plane proof

For a zero `s` with `s.re <= 0`, the reflected point `1 - s` lies in the closed
nonvanishing half-plane. Hence `riemannZeta (1 - s)` is nonzero, so the completed
zeta function is nonzero there. The completed functional equation transfers
that nonvanishing to `s`. Since `riemannZeta s` is zero, the real archimedean
Gamma factor must be zero. Mathlib's exact theorem `Complex.Gammaℝ_eq_zero_iff`
then forces `s` to be a negative even integer; the zero at the origin is excluded
using `riemannZeta_zero`.

This closes an established prerequisite. It does not constrain zeros more
tightly than classical theory and therefore is not new progress on RH itself.

## New frontier

Functional-equation rearrangement alone has now delivered all expected
location and symmetry consequences. The remaining assertion is exactly the
open critical-line statement.

The selected formal route is an RH-equivalent error bound for the Chebyshev
function `psi`. This route has the strongest pinned-library foundation:
Mathlib already defines `psi`, the von Mangoldt function, classical Chebyshev
bounds, and the logarithmic derivative identity for zeta on `Re(s) > 1`.

The missing bridge is substantial and precise: formalize an explicit formula
relating the `psi` remainder to nontrivial zeta zeros, then kernel-check the
classical equivalence between the square-root-scale remainder bound and RH.

`CriticalLineCriterion.lean` now defines the exact remainder and bound, records
the RH equivalence as an open proposition rather than an axiom, reconstructs the
finite von Mangoldt sum, and connects its L-series to `-zeta'/zeta` on the
right half-plane. The next proof obligation is the explicit-formula bridge.

`ZetaZeroMultiplicity.lean` begins the multiplicity-aware side of that bridge.
It defines zeta's analytic vanishing order, proves zeta is analytic at every
nontrivial zero, proves that such a zero has nonzero order, and characterizes
order zero away from the pole.

## Compact divisor milestone

`CompactZetaDivisor.lean` now constructs the integer-valued zeta divisor on any
set avoiding the pole. Lean verifies that:

1. its support is finite on compact regions;
2. its values are analytic vanishing orders;
3. all multiplicities are nonnegative;
4. zeta has finite analytic order everywhere away from `1`;
5. support membership is exactly zeta vanishing; and
6. finite weighted, multiplicity-aware zero sums are well-defined.

The explicit pole exclusion is intentional. Pinned Mathlib exposes zeta as
analytic on `{1}ᶜ`, but does not expose a global meromorphic-continuation theorem
that could justify crossing the pole silently.

## Explicit-formula interface

`ExplicitFormula.lean` constructs compact truncation regions by removing a
shrinking ball around `1` from an expanding closed ball. Each region is proved
compact and pole-free, and the regions are proved to exhaust every point away
from `1`. It then filters the divisor to nontrivial zeros, proves that every
nontrivial zero appears in some finite truncation, and defines the finite sum

`sum multiplicity(ρ) * x^ρ / ρ`.

Every selected term is proved to be a nontrivial zeta zero with strictly
positive multiplicity. The classical limiting identity with the Chebyshev
`psi` remainder, including the elementary pole/trivial-zero correction, is now
recorded precisely as `ChebyshevExplicitFormulaTarget`. It remains an open
proposition: no convergence theorem or explicit formula has been claimed.

`PerronFormula.lean` now defines the exact logarithmic-derivative kernel
`(-zeta'/zeta)(s) * x^s / s`, its normalized finite-height vertical integral,
and the corresponding von Mangoldt L-series integral. Lean proves pointwise and
finite-height equality of the two forms on every vertical line `Re(s) = c > 1`.
It also records the required convergence to `Chebyshev.psi x` as
`ChebyshevPerronInversionTarget` and proves that its zeta and von Mangoldt forms
are equivalent; the convergence itself is not claimed.

The laboratory now contains 55 kernel-checked research theorems (58
declarations including the three baseline reproduction checks). The next
irreducible proof unit is the scalar Perron kernel limit for
`y^(c+it)/(c+it)` away from `y = 1`. That is followed by finite Dirichlet
polynomial inversion, absolutely convergent tail control, the full Chebyshev
Perron limit, and finally the rectangular contour shift with residue accounting
and error bounds.

## Isolation from retention evaluation

No verified-memory record, held-out retention task, packet, model prompt, or
paid-call configuration was changed. The mathematics work is confined to new
Lean source and research metadata, so the delayed retention comparison remains
frozen and uncontaminated.

## 15 August continuation: residue gates closed

Three additional modules now reduce the classical explicit-formula bridge to
one analytic estimate.

`TrivialZeroResidues.lean` proves that all negative-even zeta zeros are simple,
identifies every local contour residue, proves summability, and evaluates their
complete contribution as `-(1/2) * log (1 - x⁻¹ ^ 2)` for `x > 1`.

`RectangularResidues.lean` proves directly that the project's positively
oriented rectangular boundary integral of `(s-p)⁻¹` is `2*pi*I` for a strictly
interior pole. It lifts the kernel calculation to a finite global residue
theorem for a holomorphic remainder plus finitely many principal parts, with
edge integrability discharged from continuity and strict containment.

`ExplicitFormulaAssembly.lean` records the exact admissible-height contour
limit still required and proves that this one target implies the complete
`ChebyshevExplicitFormulaTarget`. The Perron limit, residue arithmetic, and
final limit algebra are therefore no longer open.

Full verification at that checkpoint passed: 3,593 build jobs.

## 15 August continuation: actual zeta principal parts instantiated

Four further modules now close the analytic-packaging part of the contour
shift.

`MeromorphicPrincipalPart.lean` proves a general pole-removal theorem directly
from meromorphic order: if `(z-p)F(z)` tends to `r`, then
`F(z)-r/(z-p)` has an analytic extension through `p`.

`FinitePrincipalParts.lean` patches finitely many such local extensions into a
single globally analytic remainder. This step includes the finite isolation
argument needed to replace the values at all poles consistently; it is not an
assumed global residue theorem.

`ZetaContourPrincipalParts.lean` proves that zeta and the complete contour
kernel are meromorphic at every complex point. It instantiates the removal
theorem at the pole `1`, the Perron pole `0`, every negative-even trivial zero,
and every nontrivial zero with its full analytic multiplicity. A finite pole
ledger satisfying those four classifications now yields one analytic
remainder for the actual kernel

`-(zeta'/zeta)(s) * x^s / s`.

`ContourEdgeEstimates.lean` proves the exact norm identity

`||kernel(s)|| = ||zeta'/zeta(s)|| * x^Re(s) / ||s||`,

derives the pointwise bound from any supplied logarithmic-derivative estimate,
proves uniform horizontal and vertical interval-integral bounds, and proves
that a vanishing sequence of uniform horizontal bounds makes the actual edge
integrals tend to zero.

Full verification now passes: **3,599 build jobs**. The finite
principal-parts instantiation requested at the previous checkpoint is
complete. The remaining classical gate is narrower and substantive:

1. prove an admissible-height theorem giving a uniform bound for
   `zeta'/zeta` on the horizontal strips while avoiding zero ordinates;
2. use the proved norm reductions to discharge the top and bottom edges;
3. combine the zeta functional equation, gamma-factor estimates, and a
   displaced-left sequence to make the left edge vanish; and
4. identify each finite rectangular pole ledger with the project's compact
   multiplicity-aware zero truncation.

Pinned Mathlib supplies local zeta analysis but not the required global
large-height growth theorem. Consequently the complete explicit formula is
not yet claimed. This checkpoint formalizes established classical analysis;
it gives no new zero-free information and no evidence that RH is solved.

## 15 August continuation: geometric heights and exact edge assembly

Four further modules now separate the completed geometric work from the
remaining quantitative analytic number theory.

`AdmissibleHeights.lean` constructs, for every natural `n`, a height `T_n` in
`(n+2,n+3)` at which the complete horizontal line contains no zeta zero.  The
proof uses compact discreteness of the zeta zero set, the classification of
nonpositive-real-part zeros as negative-even trivial zeros, and the critical
strip location of every nontrivial zero.  Conjugation gives the corresponding
lower line, and Lean proves `T_n -> infinity`.  Continuity then supplies a
finite uniform bound for `zeta'/zeta` on every fixed compact segment of each
selected line.  This is a geometric zero-avoidance theorem, not yet the
quantitative admissible-height theorem used in the classical explicit-formula
proof.

`AdmissibleHeightBounds.lean` records the exact missing rate as
`ZetaAdmissibleHeightGrowthTarget`: on each fixed strip, a common upper/lower
bound `B_n` must satisfy `B_n/T_n -> 0`.  Lean proves that this hypothesis makes
both fixed-strip horizontal kernel integrals vanish.

`DisplacedLeftEdge.lean` selects the negative odd vertical lines
`Re(s)=-(2n+1)`, proves they tend to negative infinity, and proves that no zeta
zero lies on any such line.  It isolates the functional-equation/gamma-factor
decay statement and proves that this statement makes the oriented left-edge
integral vanish.

`AdmissibleContourEdges.lean` fixes the signs of the bottom, top, and left
edges exactly as they occur in the project's rectangle definition.  It proves
that their normalized sum tends to zero from the two remaining edge-decay
inputs.  This prevents the final contour shift from concealing an orientation
or normalization assumption.

Full verification passes: **3,603 build jobs**.  The remaining gate has not
disappeared: the fixed-strip theorem must be strengthened to the expanding
horizontal interval whose left endpoint tends to negative infinity, and the
displaced-left kernel decay must be proved from the zeta functional equation
and quantitative Gamma estimates.  The selected geometric height is only
known to avoid zeros; no separation rate from nearby zeros has yet been proved.
After those estimates, the finite rectangle ledger still has to be aligned
with the compact nontrivial-zero truncation and the vanishing tail of the
trivial-zero series.  Therefore the complete explicit formula and the
classical RH frontier are not yet claimed.

## 15 August continuation: completed-zeta growth and local Jensen control

`CompletedZetaGrowth.lean` now derives a genuinely global growth layer from
Mathlib's Mellin construction of the pole-removed completed zeta function.
The modified theta kernel is Mellin-integrable at every complex parameter.
After rewriting the Mellin transform as a Fourier transform, Lean proves an
ordinate-independent `L1` bound on every vertical line and then a uniform
bound on every fixed closed vertical strip.

The module constructs an entire xi-type function

`Xi(s) = s(s-1) completedRiemannZeta0(s) + 1`,

proves that it agrees with `s(s-1) completedRiemannZeta(s)` away from `0` and
`1`, proves that every nontrivial zeta zero is a zero of `Xi`, and proves that
`Xi` is nonzero on `Re(s)>1`.  It then instantiates Mathlib's Jensen formula
with an explicit boundary majorant.  At every height `T`, the radius-three
disk centered at `2+iT` now has a kernel-checked divisor bound, and every
nontrivial zero with `|Im(rho)-T| <= 1` is proved to lie in that disk.

Full verification passes: **3,632 build jobs**.  This closes the previously
missing qualitative entire-function and local-zero-count infrastructure.  It
does **not** yet give the quantitative `O(log T)` local zero count needed for
the standard admissible-height argument: the present Jensen quotient contains
the center value `|Xi(2+iT)|`.  Controlling its ratio to the boundary majorant
requires a vertical complex-Gamma/Stirling estimate (or an equivalent sharp
completed-zeta estimate).  The pinned Mathlib revision contains factorial
Stirling bounds but no complex-Gamma vertical asymptotic, digamma growth
theorem, or global `zeta'/zeta` estimate.

Accordingly, no assumption or opaque axiom has been inserted to manufacture
the final contour limit.  The remaining classical dependency is now exposed
at theorem level: prove the sharp center-to-boundary Jensen ratio, derive the
uniform local zero count and quantitative zero separation, and use it with the
functional equation to discharge the horizontal and displaced-left edges.
The complete Chebyshev explicit formula and the classical RH frontier remain
open until that estimate is kernel-checked.  No new RH mathematics is claimed.

## 15 August continuation: normalized xi boundary bounds

`NormalizedXiThreeLines.lean` now completes the sharp boundary-data layer for
the strip argument.  Lean proves the functional symmetry of the entire
xi-type function and introduces the fourth-power normalization

`Xi(s)/(s+4)^4`.

The fourth power is essential: after the exponential Gamma decay is cancelled
by the analytic weight `exp(-i*pi*s/4)`, it also absorbs the remaining
polynomial growth.  The only denominator zero is `s=-4`, strictly outside the
working strip `-3 <= Re(s) <= 4`.

The module proves differentiability and continuity on the strip closure,
constructs an explicit global bound for the unweighted normalized xi function,
and proves a uniform zeta bound on `Re(s)>=4` directly from absolute
convergence of its Dirichlet series.  Exact norm bookkeeping then gives a
height-independent bound for the exponentially weighted normalized xi
function on the complete right boundary `Re(s)=4`.

Complex-Gamma norm invariance under conjugation is formalized, and the xi
functional equation transfers the estimate to a height-independent bound on
the complete left boundary `Re(s)=-3`.  Thus both sharp boundary hypotheses
required by the strip principle are now kernel-checked.

The remaining step in this subchain is no longer Gamma or boundary analysis:
apply a Gaussian-regularized Hadamard three-lines argument (or the existing
Phragmen--Lindelof strip theorem) to propagate these two bounds through the
closed strip, then remove the regularizer.  The propagated polynomial-times-
exponential xi estimate must then be combined with the exact center lower
bound in Jensen's formula.  No `O(log T)` zero-count theorem, complete explicit
formula, or RH claim is made at this checkpoint.

## 15 August continuation: exact complex-Gamma vertical decay

`ComplexGammaVertical.lean` begins the final quantitative classical layer
without postulating a general Stirling expansion.  Euler's complex reflection
formula, the Gamma recurrence, and conjugation are combined to prove the exact
identity

`|Gamma(1+it)|^2 = pi*t/sinh(pi*t)` for `t>0`.

The recurrence then gives the corresponding exact identity on `Re(s)=2`, and
the definition of Deligne's `GammaR` factor gives an exact squared-norm formula
on `Re(s)=4`.  Lean additionally proves the elementary exponential estimate

`exp(x)/4 <= sinh(x)` for `x>=1`,

and hence an explicit exponentially decaying upper bound for
`|Gamma(1+it)|^2`.  These results recover precisely the vertical exponential
decay discarded by the earlier coarse Mellin-strip majorant.

This is a strict reduction of the remaining task.  Instead of first building
the complete general complex Stirling asymptotic, the programme can normalize
the entire xi function by a pole-free polynomial factor, establish sharp
bounds on the integer boundary lines, and propagate them through the strip
using Mathlib's existing Hadamard three-lines theorem.  The resulting sharp
xi bound must still be assembled and inserted into Jensen's formula before an
`O(log T)` local zero count can be claimed.  The explicit formula and RH remain
open; this checkpoint is established classical Gamma analysis only.

## 15 August continuation: Gaussian three-lines propagation

`NormalizedXiThreeLines.lean` now closes the three-lines step itself.  The
module introduces the Gaussian regularization

`exp(epsilon*s^2) exp(-i*pi*s/4) Xi(s)/(s+4)^4`,

proves a global bound on the complete closed strip for every `epsilon>0`, and
checks all analyticity, closure-continuity, and boundedness hypotheses of
Mathlib's Hadamard three-lines theorem.  The equal boundary bounds propagate
through the strip.  Lean then sends `epsilon` to zero through positive values
and obtains the unregularized estimate

`|Xi(s)| <= C |s+4|^4 exp(-pi*Im(s)/4)`

for `-3 <= Re(s) <= 4`.  This is a theorem, not a target interface.  Full
verification passed with **3,643 jobs** and no `sorry`, `admit`, or new axioms.
Commit: `4c52aa91`.

## 15 August continuation: quantitative Jensen-centre data

`QuantitativeJensen.lean` supplies the lower half of the Jensen quotient at
the moving centre `2+iT`.  The Möbius L-series identity

`zeta(s) L(mu,s) = 1`

is combined with absolute termwise domination by the Basel series to prove

`1 <= (pi^2/6) |zeta(2+iT)|`.

The module also proves the exact `GammaR` norm identity at `2+2it`, the
matching exponential lower bound obtained from `sinh(x) <= exp(x)/2`, and the
exact factorization of `|Xi(2+iT)|`.  These results rigorously provide the
centre estimate needed to cancel the archimedean exponential in Jensen's
quotient.  The full project build passed with **3,683 jobs**.  Commits:
`f6a10781` and `dcb26fc3`.

The Jensen geometry revealed an additional domain requirement that must not
be suppressed: the already-instantiated radius-four circle centred at
`2+iT` reaches `Re(s)=6`, whereas the first sharp strip theorem ends at
`Re(s)=4`.  The exact Gamma recurrence has therefore also been extended to
`Gamma(3+it)` and `GammaR(6+2it)`.  The next valid step is to propagate the
corresponding right-boundary estimate across the wider symmetric strip (or an
equivalent extension strip), and only then form the quantitative Jensen
quotient.  Until that domain extension is checked, `N(T+1)-N(T)=O(log T)` and
the subsequent contour limits remain unproved.  No RH progress is claimed.

`ExtendedXiStrip.lean` now completes the exact norm ledger on that required
right boundary.  With the sixth-power normalization it proves a uniform
high-ordinate bound for

`exp(-i*pi*s/4) Xi(s)/(s+4)^6`

on `Re(s)=6`; all exponential and polynomial factors are explicitly
cancelled.  Full verification passes with **3,684 jobs**.  What remains in
this local substep is the Gaussian three-lines propagation from `Re(s)=4` to
`Re(s)=6` (and the functional-equation transfer on the left), not any further
Gamma asymptotic.

## 15 August continuation: full Jensen-circle propagation

`ExtendedXiStrip.lean` now completes the Gaussian-regularized Hadamard
propagation on `4 <= Re(s) <= 6`, removes the regulator, and proves the sharp
polynomial-times-exponential xi estimate throughout the extension strip.
Together with the earlier `-3 <= Re(s) <= 4` theorem, this covers the complete
radius-four Jensen circle centred at `2+iT`.  Commit: `d3249ebf`.

`SharpJensenZeroCount.lean` performs the complete circle geometry and
instantiates Mathlib's Jensen theorem with the sharp boundary majorant and
verified nonzero centre.  The radius-three xi divisor therefore has a fully
quantitative Jensen bound with no remaining boundary-growth interface.  Full
verification passes with **3,685 jobs**, no `sorry`, no `admit`, and no new
axioms.  Commit: `6e339453`.

The next theorem is the asymptotic simplification of this verified quotient
using the already-proved Möbius lower bound and exact centre Gamma estimate.
Only after that quotient is proved `O(log T)` may the local zero count be
stated asymptotically.  Quantitative gap selection, the partial-fraction
logarithmic-derivative estimate, expanding horizontal edges, and the
displaced-left limit remain downstream; none is claimed at this checkpoint.

`SharpJensenZeroCount.lean` now also proves the explicit squared lower bound
for `|Xi(2+iT)|`.  It combines the Möbius reciprocal estimate, the exact
Gamma lower estimate, and verified lower bounds for both elementary xi
factors.  Full verification remains **3,685 jobs** with no `sorry`, `admit`,
or new axioms.  Commit: `763748b7`.

This exposed a normalization detail important for the asymptotic conclusion:
Mathlib's Jensen inequality requires a boundary constant at least one.  Taking
`max 1` before dividing by the exponentially small centre destroys the desired
logarithmic estimate.  The valid next step is to apply Jensen to xi normalized
by its nonzero centre value; its centre is then exactly one and the exponential
factors cancel before the `max 1` operation.  The divisor is unchanged because
the normalizing scalar is nonzero.  The `O(log T)` theorem is not claimed until
that scaled-divisor argument is checked.
