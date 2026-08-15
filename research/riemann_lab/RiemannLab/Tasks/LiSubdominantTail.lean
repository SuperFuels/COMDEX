import RiemannLab.Tasks.LiExpansiveModeIsolation
import Mathlib.Analysis.SpecificLimits.Basic

namespace RiemannLab

open Filter Topology

/-!
# Exponential domination of the subdominant zero tail

The finite dominant cluster has already been isolated exactly.  This file
formalizes the mechanism for the remainder: any tail admitting a fixed
summable envelope at rate `r` is eventually overwhelmed by a target growing
at a strictly larger rate `R`.
-/

/-- A strict spectral gap makes the normalized exponential envelope tend to
zero. -/
theorem tendsto_const_mul_ratio_pow_zero
    {C r R : ℝ} (hr : 0 ≤ r) (hR : 0 < R) (hgap : r < R) :
    Tendsto (fun n : ℕ ↦ C * (r / R) ^ n) atTop (𝓝 0) := by
  have hratio0 : 0 ≤ r / R := div_nonneg hr hR.le
  have hratio1 : r / R < 1 := (div_lt_one hR).mpr hgap
  simpa using
    (tendsto_pow_atTop_nhds_zero_of_lt_one hratio0 hratio1).const_mul C

/-- Quantitative exponential-gap domination in the original, unnormalized
coordinates. -/
theorem eventually_const_mul_pow_lt
    {A C r R : ℝ} (hA : 0 < A) (hr : 0 ≤ r)
    (hR : 0 < R) (hgap : r < R) :
    ∀ᶠ n : ℕ in atTop, C * r ^ n < A * R ^ n := by
  have hlim := tendsto_const_mul_ratio_pow_zero (C := C) hr hR hgap
  have hev : ∀ᶠ n : ℕ in atTop, C * (r / R) ^ n < A :=
    (tendsto_order.1 hlim).2 A hA
  filter_upwards [hev] with n hn
  have hRpow : 0 < R ^ n := pow_pos hR n
  calc
    C * r ^ n = (C * (r / R) ^ n) * R ^ n := by
      rw [div_pow]
      field_simp [hR.ne']
    _ < A * R ^ n := mul_lt_mul_of_pos_right hn hRpow

/-- If a complete subdominant tail is bounded by `C*r^n`, it is eventually
strictly smaller than the target magnitude `A*R^n`. -/
theorem eventually_tail_lt_target
    {tail : ℕ → ℝ} {A C r R : ℝ}
    (hA : 0 < A) (hr : 0 ≤ r) (hR : 0 < R) (hgap : r < R)
    (htail : ∀ n, tail n ≤ C * r ^ n) :
    ∀ᶠ n : ℕ in atTop, tail n < A * R ^ n := by
  filter_upwards [eventually_const_mul_pow_lt hA hr hR hgap] with n hn
  exact (htail n).trans_lt hn

/-- The contradiction-ready sign form: a negative expansive target plus a
subdominant remainder is eventually strictly negative. -/
theorem eventually_negative_target_add_tail
    {tail : ℕ → ℝ} {A C r R : ℝ}
    (hA : 0 < A) (hr : 0 ≤ r) (hR : 0 < R) (hgap : r < R)
    (htail : ∀ n, tail n ≤ C * r ^ n) :
    ∀ᶠ n : ℕ in atTop, -A * R ^ n + tail n < 0 := by
  filter_upwards [eventually_tail_lt_target hA hr hR hgap htail] with n hn
  linarith

/-- A two-sided absolute-value envelope is sufficient for the same strict
negative conclusion. -/
theorem eventually_negative_target_add_abs_bounded_tail
    {tail : ℕ → ℝ} {A C r R : ℝ}
    (hA : 0 < A) (hr : 0 ≤ r) (hR : 0 < R) (hgap : r < R)
    (htail : ∀ n, |tail n| ≤ C * r ^ n) :
    ∀ᶠ n : ℕ in atTop, -A * R ^ n + tail n < 0 := by
  apply eventually_negative_target_add_tail hA hr hR hgap
  intro n
  exact (le_abs_self (tail n)).trans (htail n)

/-! ## Building the envelope from an infinite weighted mode family -/

/-- A summable family of nonnegative weights and uniformly subdominant rates
has a complete infinite sum bounded by one exponential envelope. -/
theorem tsum_weight_mul_rate_pow_le
    {ι : Type*} [Countable ι]
    (weight rate : ι → ℝ) {r : ℝ}
    (hweight : Summable weight) (hweight0 : ∀ i, 0 ≤ weight i)
    (hrate0 : ∀ i, 0 ≤ rate i) (hrate : ∀ i, rate i ≤ r)
    (n : ℕ) :
    ∑' i, weight i * rate i ^ n ≤ (∑' i, weight i) * r ^ n := by
  have hpoint : ∀ i, weight i * rate i ^ n ≤ weight i * r ^ n := by
    intro i
    apply mul_le_mul_of_nonneg_left _ (hweight0 i)
    exact pow_le_pow_left₀ (hrate0 i) (hrate i) n
  have hupper : Summable (fun i ↦ weight i * r ^ n) :=
    Summable.mul_right (r ^ n) hweight
  have hlower : Summable (fun i ↦ weight i * rate i ^ n) :=
    hupper.of_nonneg_of_le
      (fun i ↦ mul_nonneg (hweight0 i) (pow_nonneg (hrate0 i) n)) hpoint
  have hsum := hlower.tsum_le_tsum hpoint hupper
  simpa [hweight.tsum_mul_right] using hsum

/-- Combining the summable-family envelope with a strict spectral gap gives
eventual domination of the entire infinite family by the selected target. -/
theorem eventually_tsum_subdominant_lt_target
    {ι : Type*} [Countable ι]
    (weight rate : ι → ℝ) {A r R : ℝ}
    (hweight : Summable weight) (hweight0 : ∀ i, 0 ≤ weight i)
    (hrate0 : ∀ i, 0 ≤ rate i) (hrate : ∀ i, rate i ≤ r)
    (hA : 0 < A) (hr0 : 0 ≤ r) (hR : 0 < R) (hgap : r < R) :
    ∀ᶠ n : ℕ in atTop,
      ∑' i, weight i * rate i ^ n < A * R ^ n := by
  apply eventually_tail_lt_target hA hr0 hR hgap
  intro n
  exact tsum_weight_mul_rate_pow_le weight rate hweight hweight0
    hrate0 hrate n

end RiemannLab
