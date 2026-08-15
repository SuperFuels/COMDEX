import RiemannLab.Tasks.ZetaAmplifierSummability

namespace RiemannLab

open Filter Topology

/-!
# Assembly of a negative channel with the complete actual zeta tail

This module performs the final sign bookkeeping.  Once a channel coefficient
is identified with the selected target's localized quartet contribution, the
verified two-sided tail theorem makes the full zero-side form eventually
negative.  The separate target-identification hypothesis is kept explicit.
-/

/-- The four real coefficients supplied by phase removal. -/
noncomputable def fourChannelDefect (w : ℂ) (b : ℝ) : Fin 4 → ℝ
  | ⟨0, _⟩ => -4 * b ^ 2 * (w ^ 2).re
  | ⟨1, _⟩ => -4 * b ^ 2 * (((Complex.I * (b : ℂ)) * w) ^ 2).re
  | ⟨2, _⟩ => -4 * b ^ 2 *
      ((((1 : ℂ) + Complex.I * (b : ℂ)) * w) ^ 2).re
  | ⟨3, _⟩ => -4 * b ^ 2 *
      ((((-1 : ℂ) + Complex.I * (b : ℂ)) * w) ^ 2).re

/-- A nonzero localized transverse target has a strictly negative channel. -/
theorem exists_negative_fourChannelDefect
    {w : ℂ} {b : ℝ} (hw : w ≠ 0) (hb : b ≠ 0) :
    ∃ channel : Fin 4, fourChannelDefect w b channel < 0 := by
  rcases four_channel_quartet_defect_negative hw hb with h | h | h | h
  · exact ⟨⟨0, by omega⟩, h⟩
  · exact ⟨⟨1, by omega⟩, h⟩
  · exact ⟨⟨2, by omega⟩, h⟩
  · exact ⟨⟨3, by omega⟩, h⟩

/-- Pure final assembly: a negative leading coefficient at rate `R` plus a
tail strictly smaller than its absolute coefficient is eventually negative. -/
theorem eventually_negative_channel_add_tail
    {D R : ℝ} {tail : ℕ → ℝ}
    (hD : D < 0) (hR : 0 < R)
    (htail : ∀ᶠ n : ℕ in atTop, tail n < (-D) * R ^ n) :
    ∀ᶠ n : ℕ in atTop, D * R ^ n + tail n < 0 := by
  filter_upwards [htail] with n hn
  have hpow : 0 ≤ R ^ n := (pow_nonneg hR.le n)
  nlinarith

/-- The finite four-channel certificate and the complete actual zeta-tail
theorem are now joined in one statement.  The coefficient `D` is explicit;
to obtain the literal Weil witness one must identify this coefficient with
the selected target quartet in the arithmetic test-function normalization. -/
theorem not_rh_fourChannel_tail_assembly
    (hRH : ¬RiemannHypothesis)
    (competitors : Finset ℂ) (a : ℂ) (mode : ℕ)
    {w : ℂ} {b : ℝ} (hw : w ≠ 0) (hb : b ≠ 0) :
    ∃ target : NontrivialZetaZeroPoint, ∃ r : ℝ, ∃ channel : Fin 4,
      1 < r ∧ r < zetaLiRate target ∧
      fourChannelDefect w b channel < 0 ∧
      ∀ᶠ n : ℕ in atTop,
        fourChannelDefect w b channel * zetaLiRate target ^ n +
          (∑' ρ : SubdominantZetaZeroPoints r,
            zetaModeWeight
              (fun z ↦ localizedZetaAmplifier competitors a mode z.1) ρ.1 *
              zetaLiRate ρ.1 ^ n) < 0 := by
  obtain ⟨channel, hchannel⟩ := exists_negative_fourChannelDefect hw hb
  obtain ⟨target, r, hr, hrt, _hfinite, htail⟩ :=
    not_rh_localizedZetaAmplifier_tail_dominated
      hRH competitors a mode
  refine ⟨target, r, channel, hr, hrt, hchannel, ?_⟩
  apply eventually_negative_channel_add_tail hchannel
    (lt_trans (lt_trans zero_lt_one hr) hrt)
  exact htail (-fourChannelDefect w b channel) (neg_pos.mpr hchannel)

end RiemannLab
