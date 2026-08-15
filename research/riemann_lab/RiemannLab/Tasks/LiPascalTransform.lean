import RiemannLab.Tasks.LiWeilBasis

namespace RiemannLab

open scoped BigOperators

/-!
# Pascal coordinates for Li modes

The Li coefficients are a binomial transform of reciprocal-zero power sums.
This file records the finite algebra behind undoing that transform.  It does
not perform the analytic zero sum and makes no assumption about RH.
-/

/-- The alternating Pascal transform of a geometric sequence isolates one
power.  This is the algebraic core of the reciprocal-zero coordinate change. -/
theorem inversePascal_geometric (x : ℂ) (n : ℕ) :
    (∑ k ∈ Finset.range (n + 1),
        (n.choose k : ℂ) * (-1 : ℂ) ^ (n - k) * (1 - x) ^ k) =
      (-x) ^ n := by
  have h := (add_pow (1 - x) (-1 : ℂ) n).symm
  rw [show (1 - x) + (-1 : ℂ) = -x by ring] at h
  simpa [mul_comm, mul_left_comm, mul_assoc] using h

/-- Therefore inverse Pascal transformation sends the elementary Li mode
`1 - (1-x)^k` to a signed monomial, apart from the exceptional zeroth row. -/
theorem inversePascal_liMode (x : ℂ) (n : ℕ) (hn : n ≠ 0) :
    (∑ k ∈ Finset.range (n + 1),
        (n.choose k : ℂ) * (-1 : ℂ) ^ (n - k) * (1 - (1 - x) ^ k)) =
      -(-x) ^ n := by
  simp_rw [mul_sub]
  rw [Finset.sum_sub_distrib]
  have hconstant :
      (∑ k ∈ Finset.range (n + 1),
          (n.choose k : ℂ) * (-1 : ℂ) ^ (n - k) * 1) = 0 := by
    simpa [mul_comm, mul_left_comm, mul_assoc, hn] using
      (add_pow (1 : ℂ) (-1) n).symm
  rw [hconstant, inversePascal_geometric]
  ring

/-- Applied to the actual Li zero mode, Pascal inversion exposes the reciprocal
power `ρ⁻ⁿ` (up to the explicit alternating sign). -/
theorem inversePascal_liZeroMode (ρ : ℂ) (n : ℕ) (hn : n ≠ 0) :
    (∑ k ∈ Finset.range (n + 1),
        (n.choose k : ℂ) * (-1 : ℂ) ^ (n - k) * liZeroMode k ρ) =
      -(-ρ⁻¹) ^ n := by
  simpa [liZeroMode] using inversePascal_liMode ρ⁻¹ n hn

end RiemannLab
