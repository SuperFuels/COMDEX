# AION RH Programme — Scalar Perron Formalization Progress

**Date:** 15 August 2026  
**Authority:** Lean 4.24.0 kernel with pinned Mathlib v4.32.1  
**Build:** PASS, 3,586 jobs
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

## Sharp convergence subsequently completed

The required Dirichlet-type control has now been formalized in
`RiemannLab/Tasks/OscillatoryCauchy.lean`. Lean proves an exact finite-interval
integration-by-parts identity. Its endpoint term is bounded by
\(1/(|a|T)\), and its squared-denominator remainder is absolutely integrable.
Consequently both the one-sided and normalized symmetric sharp truncations
converge for every \(c>0\) and \(a\ne0\).

The original scalar target is now equivalent to a single explicit identity

\[
L(c,a)=\begin{cases}e^{-ac},&a>0,\\0,&a<0,\end{cases}
\]

where \(L(c,a)\) is a fully defined, absolutely convergent remainder
expression. Conditional convergence and tail control are no longer open. The
remaining work is the classical value evaluation of \(L(c,a)\).

## Absolute-integrability reduction completed

Lean now goes one step further. It proves the exact Laplace representation

\[
\frac{1}{c+it}=\int_0^\infty e^{-(c+it)u}\,du
\]

and performs symmetric integration by parts to replace the conditional kernel
by

\[
S(c,a,t)=\frac{e^{iat}}{(c+it)^2}.
\]

The new kernel is absolutely integrable on the whole real line, and the sharp
limit value satisfies the kernel-checked identity

\[
L(c,a)=\frac{1}{2\pi a}\int_{-\infty}^{\infty}
  \frac{e^{iat}}{(c+it)^2}\,dt.
\]

The remaining theorem is therefore exactly

\[
\int_{-\infty}^{\infty}\frac{e^{iat}}{(c+it)^2}\,dt
=
\begin{cases}
2\pi a e^{-ac},&a>0,\\
0,&a<0.
\end{cases}
\]

Lean also verifies that this named squared-kernel value target is sufficient
to close the original oscillatory Cauchy target. No conditional convergence,
tail estimate, or normalization ambiguity remains in that final gate.

## Claim boundary

This is serious formal-engineering progress on a classical analytic bridge. It
does not prove the away-from-jump scalar Perron limit, the Chebyshev Perron
formula, an RH-equivalent estimate, or the Riemann Hypothesis. No new
mathematics or AION superiority is claimed.
