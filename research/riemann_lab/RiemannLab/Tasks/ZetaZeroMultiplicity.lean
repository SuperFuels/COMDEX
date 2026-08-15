import RiemannLab.Tasks.NontrivialZeros
import Mathlib.Analysis.Analytic.Order

namespace RiemannLab

/-!
Multiplicity-aware infrastructure for zeta zeros. We use the analytic order in
`ℕ∞`; proving finite support on compact regions and integrating this with the
complex divisor API are the next explicit-formula milestones.
-/

/-- Analytic vanishing order of zeta at a point. -/
noncomputable def zetaZeroOrder (s : ℂ) : ℕ∞ :=
  analyticOrderAt riemannZeta s

/-- Zeta is analytic at every nontrivial zero. -/
theorem IsNontrivialZetaZero.analyticAt {s : ℂ}
    (hs : IsNontrivialZetaZero s) : AnalyticAt ℂ riemannZeta s := by
  apply analyticOn_riemannZeta
  intro hs1
  subst s
  have hlt := hs.re_lt_one
  norm_num at hlt

/-- A nontrivial zero has nonzero analytic vanishing order. -/
theorem IsNontrivialZetaZero.zetaZeroOrder_ne_zero {s : ℂ}
    (hs : IsNontrivialZetaZero s) : zetaZeroOrder s ≠ 0 := by
  exact analyticOrderAt_ne_zero.mpr ⟨hs.analyticAt, hs.1⟩

/-- Away from the pole, vanishing order zero is equivalent to zeta being nonzero. -/
theorem zetaZeroOrder_eq_zero_iff {s : ℂ} (hs : s ≠ 1) :
    zetaZeroOrder s = 0 ↔ riemannZeta s ≠ 0 := by
  unfold zetaZeroOrder
  apply AnalyticAt.analyticOrderAt_eq_zero
  exact analyticOn_riemannZeta s (by simpa using hs)

end RiemannLab
