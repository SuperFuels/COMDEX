# AION RH Programme — Scalar Perron Formalization Progress

**Date:** 15 August 2026  
**Authority:** Lean 4.24.0 kernel with pinned Mathlib v4.32.1  
**Build:** PASS, 3,585 jobs  
**External/API calls:** 0

## Completed formal work

The scalar Perron layer is now a dedicated Lean module at
`research/riemann_lab/RiemannLab/Tasks/ScalarPerron.lean`. It contains eight
formal definitions and twenty-one kernel-checked theorems, with no `sorry`,
`admit`, project axiom, or unsafe declaration.

For (c>0), (y>0), and real height (t), the module defines

\[
K(c,y,t)=\frac{y^{c+it}}{c+it},\qquad
Q_T(c,y)=\frac1{2\pi}\int_{-T}^{T}K(c,y,t)\,dt.
\]

It proves that the vertical line avoids the pole, that the kernel is continuous,
and that every finite truncation is a legitimate interval integral. After the
substitution (a=\log y), Lean verifies the exact identities

\[
K(c,y,t)=\frac{e^{a(c+it)}}{c+it}
=e^{ac}\frac{e^{iat}}{c+it}
\]

and their finite-height integral counterparts. The original scalar limit target
is also proved logically equivalent to its nonzero-frequency logarithmic form.

## Normalization benchmark proved

Although the main target excludes the jump (y=1), the symmetric jump value is
now completely checked. Lean proves

\[
\int_{-T}^{T}\frac{dt}{c+it}=2\arctan(T/c),
\qquad
Q_T(c,1)=\frac{\arctan(T/c)}{\pi},
\]

and therefore

\[
Q_T(c,1)\longrightarrow \frac12.
\]

This verifies the orientation, (2\pi) normalization, symmetric truncation,
and classical half-weight convention at the discontinuity.

## Exact remaining gate

The nonzero-frequency conditional limit is not yet proved. In the reduced form
the required theorem is

\[
\frac1{2\pi}\int_{-T}^{T}\frac{e^{iat}}{c+it}\,dt
\longrightarrow
\begin{cases}
e^{-ac},&a>0,\\
0,&a<0.
\end{cases}
\]

The integrand has only (1/|t|) decay. Consequently the directly available
Mathlib Fourier inversion theorem, which requires absolute integrability of the
transform, cannot close this gate. The next proof must supply a genuine
Dirichlet-type sharp-truncation estimate or prove a comparison with an
appropriate regularization.

## Claim boundary

This is serious formal-engineering progress on a classical analytic bridge. It
does not prove the away-from-jump scalar Perron limit, the Chebyshev Perron
formula, an RH-equivalent estimate, or the Riemann Hypothesis. No new
mathematics or AION superiority is claimed.
