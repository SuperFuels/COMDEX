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
theorems for the selected Chebyshev route. Together with the earlier foundation,
the laboratory now contains 34 kernel-checked theorems.

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
order zero away from the pole. The next unit is a finite compact zeta divisor
that can participate in residue sums.

## Isolation from retention evaluation

No verified-memory record, held-out retention task, packet, model prompt, or
paid-call configuration was changed. The mathematics work is confined to new
Lean source and research metadata, so the delayed retention comparison remains
frozen and uncontaminated.
