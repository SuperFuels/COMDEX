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
