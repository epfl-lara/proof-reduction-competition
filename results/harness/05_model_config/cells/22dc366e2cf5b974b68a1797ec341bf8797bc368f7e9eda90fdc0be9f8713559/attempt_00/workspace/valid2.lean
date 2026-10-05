lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  funext a
  by_contra ha
  have hc := Continuous.inner' (𝕜 := ℝ) f (fun _ => f a) hf continuous_const
  have hp : 0 < ⟪f a, f a⟫_ℝ :=
    lt_of_le_of_ne real_inner_self_nonneg' (fun h => ha (inner_self_eq_zero'.mp h.symm))
  obtain ⟨r, hr, hball⟩ := Metric.isOpen_iff.mp
    (isOpen_lt continuous_const hc) a hp
  let b : ContDiffBump a := ⟨r / 2, r, half_pos hr, half_lt_self hr⟩
  have hb : IsTestFunction (b : Y → ℝ) := ⟨b.contDiff, b.hasCompactSupport⟩
  have hc' := b.continuous.mul hc
  have hi := hc'.integrable_of_hasCompactSupport (μ := μ) b.hasCompactSupport.mul_right
  have hn : ∀ x, 0 ≤ b x * ⟪f x, f a⟫_ℝ := by
    intro x
    by_cases hx : x ∈ Metric.ball a r
    · exact mul_nonneg b.nonneg (hball hx).le
    · rw [b.zero_of_le_dist (le_of_not_gt hx), zero_mul]
  have hpos := integral_pos_of_integrable_nonneg_nonzero hc' hi hn
    (mul_ne_zero (ne_of_gt (b.pos_of_mem_ball (Metric.mem_ball_self hr)))
      (ne_of_gt hp))
  have hz := hg (fun x => b x • f a) (hb.smul_right contDiff_const)
  simp only [inner_smul_right'] at hz
  exact (ne_of_gt hpos) hz
