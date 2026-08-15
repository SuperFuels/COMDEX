import RiemannLab.Tasks.LiStationaryPositiveOperator
import Mathlib.RingTheory.PowerSeries.Basic

namespace RiemannLab

open PowerSeries

/-!
# The stationary Li symbol as a Carathéodory transform

This file identifies the complete stationary lag sequence with the second
difference of the ordinary Li generating series.  It is a formal-series
identity: no convergence statement and no version of RH is assumed.
-/

/-- The ordinary generating series beginning with `a 1`. -/
noncomputable def liTailSeries (a : ℕ → ℝ) : PowerSeries ℝ :=
  PowerSeries.mk (fun n ↦ a (n + 1))

/-- The even stationary symbol: its constant coefficient is the zeroth lag
and its positive coefficients are twice the positive lags. -/
noncomputable def liStationarySymbolSeries (a : ℕ → ℝ) : PowerSeries ℝ :=
  PowerSeries.mk (fun
    | 0 => liIncrementLag a 0
    | n + 1 => 2 * liIncrementLag a (n + 1))

/-- Coefficient form of the stationary transform. -/
theorem coeff_liStationarySymbolSeries_zero (a : ℕ → ℝ) :
    PowerSeries.coeff 0 (liStationarySymbolSeries a) = a 1 - a 0 := by
  simp [liStationarySymbolSeries, liIncrementLag]

/-- Every positive coefficient is the unscaled second difference. -/
theorem coeff_liStationarySymbolSeries_succ (a : ℕ → ℝ) (n : ℕ) :
    PowerSeries.coeff (n + 1) (liStationarySymbolSeries a) =
      a n - 2 * a (n + 1) + a (n + 2) := by
  simp [liStationarySymbolSeries, liIncrementLag]
  ring

/-- Exact formal Carathéodory identity.  For a Li-type sequence with `a 0=0`,
the stationary symbol is `(1-X)^2` times the tail generating series. -/
theorem liStationarySymbolSeries_eq
    (a : ℕ → ℝ) (ha0 : a 0 = 0) :
    liStationarySymbolSeries a =
      (1 - PowerSeries.X) ^ 2 * liTailSeries a := by
  ext n
  rcases n with _ | n
  · simp [liStationarySymbolSeries, liTailSeries, liIncrementLag, ha0]
  · rw [coeff_liStationarySymbolSeries_succ]
    rw [show (1 - PowerSeries.X : PowerSeries ℝ) ^ 2 =
        1 - (2 : ℝ) • PowerSeries.X + PowerSeries.X ^ 2 by
          rw [two_smul]
          ring]
    rw [add_mul, sub_mul, one_mul]
    rw [smul_mul_assoc]
    rcases n with _ | n <;>
      simp [liTailSeries, PowerSeries.coeff_X_pow_mul', ha0] <;> ring

/-- The coefficient sequence of the stationary symbol is exactly the lag
sequence, with the conventional factor two away from the origin. -/
theorem liStationarySymbolSeries_coefficients (a : ℕ → ℝ) :
    (PowerSeries.coeff 0 (liStationarySymbolSeries a) = liIncrementLag a 0) ∧
    (∀ n : ℕ, PowerSeries.coeff (n + 1) (liStationarySymbolSeries a) =
      2 * liIncrementLag a (n + 1)) := by
  constructor
  · simp [liStationarySymbolSeries]
  · intro n
    simp [liStationarySymbolSeries]

end RiemannLab
