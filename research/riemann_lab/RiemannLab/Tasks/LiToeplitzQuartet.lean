import RiemannLab.Tasks.LiPascalTransform

namespace RiemannLab

/-!
# A three-lag Toeplitz certificate for a reflected Li quartet

After inverse-Pascal reduction, a reflected/conjugate quartet is governed by
`q`, `q⁻¹`, `conj q`, and `conj(q⁻¹)`.  If

`q + q⁻¹ = a + b i`,

then its first three real Toeplitz lags are `4`, `2a`, and
`2(a²-b²)-4`.  This file evaluates the corresponding `3 x 3` determinant and
isolates a simple sufficient condition for a negative finite certificate.
-/

/-- The lag-one entry of the real reflected/conjugate quartet. -/
noncomputable def quartetToeplitzLagOne (a : ℝ) : ℝ := 2 * a

/-- The lag-two entry, using
`q²+q⁻² = (q+q⁻¹)²-2`. -/
noncomputable def quartetToeplitzLagTwo (a b : ℝ) : ℝ :=
  2 * (a ^ 2 - b ^ 2) - 4

/-- The leading three-by-three Toeplitz block of the quartet kernel. -/
noncomputable def quartetToeplitzThree (a b : ℝ) : Matrix (Fin 3) (Fin 3) ℝ :=
  !![(4 : ℝ), quartetToeplitzLagOne a, quartetToeplitzLagTwo a b;
     quartetToeplitzLagOne a, 4, quartetToeplitzLagOne a;
     quartetToeplitzLagTwo a b, quartetToeplitzLagOne a, 4]

/-- Exact factorization of the leading three-by-three determinant.  The
factor `b²` vanishes on the unit-circle/reflection locus. -/
theorem det_quartetToeplitzThree (a b : ℝ) :
    Matrix.det (quartetToeplitzThree a b) =
      16 * b ^ 2 * (a ^ 2 - b ^ 2 - 4) := by
  rw [Matrix.det_fin_three]
  simp [quartetToeplitzThree, quartetToeplitzLagOne, quartetToeplitzLagTwo]
  ring

/-- A nonzero transverse defect `b`, together with
`a²-b²<4`, forces an explicit negative determinant. -/
theorem det_quartetToeplitzThree_neg
    {a b : ℝ} (hb : b ≠ 0) (hinside : a ^ 2 - b ^ 2 < 4) :
    Matrix.det (quartetToeplitzThree a b) < 0 := by
  rw [det_quartetToeplitzThree]
  have hb2 : 0 < b ^ 2 := sq_pos_of_ne_zero hb
  have hfactor : a ^ 2 - b ^ 2 - 4 < 0 := by linarith
  exact mul_neg_of_pos_of_neg (mul_pos (by norm_num) hb2) hfactor

/-- On the critical/unit-circle locus `b=0`, the same determinant vanishes,
as expected for a rank-two cosine Gram block. -/
theorem det_quartetToeplitzThree_of_transverse_eq_zero (a : ℝ) :
    Matrix.det (quartetToeplitzThree a 0) = 0 := by
  rw [det_quartetToeplitzThree]
  ring

/-- A sparse three-coordinate witness for the quartet block. -/
noncomputable def quartetToeplitzWitness (a : ℝ) : Fin 3 → ℝ :=
  ![1, -a, 1]

/-- The witness evaluates to the exact negative square `-4b²`.  This is
strictly stronger than the determinant test: no auxiliary condition on `a`
is required. -/
theorem quartetToeplitzWitness_quadratic (a b : ℝ) :
    dotProduct (star (quartetToeplitzWitness a))
        ((quartetToeplitzThree a b).mulVec (quartetToeplitzWitness a)) =
      -4 * b ^ 2 := by
  simp [quartetToeplitzWitness, quartetToeplitzThree,
    quartetToeplitzLagOne, quartetToeplitzLagTwo,
    Matrix.mulVec, dotProduct, Fin.sum_univ_succ]
  ring

/-- Therefore every quartet block with nonzero transverse coordinate is not
positive semidefinite, witnessed already in dimension three. -/
theorem quartetToeplitzThree_not_posSemidef
    {a b : ℝ} (hb : b ≠ 0) :
    ¬(quartetToeplitzThree a b).PosSemidef := by
  intro hpsd
  have hnonneg := hpsd.dotProduct_mulVec_nonneg (quartetToeplitzWitness a)
  rw [quartetToeplitzWitness_quadratic] at hnonneg
  have hb2 : 0 < b ^ 2 := sq_pos_of_ne_zero hb
  nlinarith

/-! ## Direct coordinates from `ρ = β + iγ` -/

/-- The positive radial quantity appearing in
`ρ(ρ-1) = -X + iC`. -/
noncomputable def quartetRadialX (β γ : ℝ) : ℝ :=
  γ ^ 2 + β * (1 - β)

/-- The transverse quantity; away from the real axis it vanishes exactly on
the critical line. -/
noncomputable def quartetTransverseC (β γ : ℝ) : ℝ :=
  γ * (2 * β - 1)

noncomputable def quartetRadialDenom (β γ : ℝ) : ℝ :=
  quartetRadialX β γ ^ 2 + quartetTransverseC β γ ^ 2

/-- Real part of `q+q⁻¹`, expressed directly in `(β,γ)` coordinates. -/
noncomputable def quartetA (β γ : ℝ) : ℝ :=
  2 - quartetRadialX β γ / quartetRadialDenom β γ

/-- Imaginary part of `q+q⁻¹`, expressed directly in `(β,γ)` coordinates. -/
noncomputable def quartetB (β γ : ℝ) : ℝ :=
  -quartetTransverseC β γ / quartetRadialDenom β γ

/-- Exact rational form of the determinant's final sign factor. -/
theorem quartetA_sq_sub_quartetB_sq_sub_four
    {β γ : ℝ} (hden : quartetRadialDenom β γ ≠ 0) :
    quartetA β γ ^ 2 - quartetB β γ ^ 2 - 4 =
      (quartetRadialX β γ ^ 2 * (1 - 4 * quartetRadialX β γ) -
        quartetTransverseC β γ ^ 2 * (1 + 4 * quartetRadialX β γ)) /
          quartetRadialDenom β γ ^ 2 := by
  unfold quartetA quartetB
  unfold quartetRadialDenom at hden ⊢
  field_simp [hden]
  ring

/-- Once `X>1/4`, the rational sign factor is strictly negative. -/
theorem quartetA_sq_sub_quartetB_sq_sub_four_neg
    {β γ : ℝ} (hX : 1 / 4 < quartetRadialX β γ) :
    quartetA β γ ^ 2 - quartetB β γ ^ 2 - 4 < 0 := by
  have hXpos : 0 < quartetRadialX β γ := by linarith
  have hdenpos : 0 < quartetRadialDenom β γ := by
    unfold quartetRadialDenom
    nlinarith [sq_nonneg (quartetTransverseC β γ)]
  have hleft :
      quartetRadialX β γ ^ 2 * (1 - 4 * quartetRadialX β γ) < 0 :=
    mul_neg_of_pos_of_neg (sq_pos_of_pos hXpos) (by linarith)
  have hright :
      0 ≤ quartetTransverseC β γ ^ 2 *
        (1 + 4 * quartetRadialX β γ) :=
    mul_nonneg (sq_nonneg _) (by linarith)
  rw [quartetA_sq_sub_quartetB_sq_sub_four hdenpos.ne']
  exact div_neg_of_neg_of_pos (by linarith) (sq_pos_of_pos hdenpos)

/-- A nonzero transverse coordinate and `X>1/4` give a negative three-lag
quartet certificate. -/
theorem det_quartetToeplitzThree_betaGamma_neg
    {β γ : ℝ} (hX : 1 / 4 < quartetRadialX β γ)
    (hC : quartetTransverseC β γ ≠ 0) :
    Matrix.det (quartetToeplitzThree (quartetA β γ) (quartetB β γ)) < 0 := by
  apply det_quartetToeplitzThree_neg
  · unfold quartetB
    have hXpos : 0 < quartetRadialX β γ := by linarith
    have hdenpos : 0 < quartetRadialDenom β γ := by
      unfold quartetRadialDenom
      nlinarith [sq_nonneg (quartetTransverseC β γ)]
    exact div_ne_zero (neg_ne_zero.mpr hC) hdenpos.ne'
  · have hfactor := quartetA_sq_sub_quartetB_sq_sub_four_neg hX
    linarith

/-- In the critical strip, every off-line quartet with `γ²≥1/4` satisfies the
three-by-three negative-determinant condition. -/
theorem det_quartetToeplitzThree_offCritical_neg
    {β γ : ℝ} (hβ0 : 0 < β) (hβ1 : β < 1)
    (hγ : 1 / 4 ≤ γ ^ 2) (hγ0 : γ ≠ 0) (hoff : β ≠ 1 / 2) :
    Matrix.det (quartetToeplitzThree (quartetA β γ) (quartetB β γ)) < 0 := by
  apply det_quartetToeplitzThree_betaGamma_neg
  · unfold quartetRadialX
    have hβprod : 0 < β * (1 - β) := mul_pos hβ0 (sub_pos.mpr hβ1)
    linarith
  · unfold quartetTransverseC
    apply mul_ne_zero hγ0
    intro h
    apply hoff
    linarith

/-- The explicit witness removes the height restriction entirely: whenever
`γ ≠ 0` and `β ≠ 1/2`, the isolated reflected/conjugate quartet block is not
positive semidefinite. -/
theorem quartetToeplitzThree_offCritical_not_posSemidef
    {β γ : ℝ} (hγ0 : γ ≠ 0) (hoff : β ≠ 1 / 2) :
    ¬(quartetToeplitzThree (quartetA β γ) (quartetB β γ)).PosSemidef := by
  apply quartetToeplitzThree_not_posSemidef
  unfold quartetB
  have hC : quartetTransverseC β γ ≠ 0 := by
    unfold quartetTransverseC
    apply mul_ne_zero hγ0
    intro h
    apply hoff
    linarith
  have hden : quartetRadialDenom β γ ≠ 0 := by
    unfold quartetRadialDenom
    have hC2 : 0 < quartetTransverseC β γ ^ 2 := sq_pos_of_ne_zero hC
    nlinarith [sq_nonneg (quartetRadialX β γ)]
  exact div_ne_zero (neg_ne_zero.mpr hC) hden

end RiemannLab
