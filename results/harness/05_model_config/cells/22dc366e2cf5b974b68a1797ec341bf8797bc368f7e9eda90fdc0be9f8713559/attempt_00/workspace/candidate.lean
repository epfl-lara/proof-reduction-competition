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
  have hc' := b.continuous.mul hc
  have hz := hg (fun x => b x • f a) (IsTestFunction.smul_right ⟨b.contDiff, b.hasCompactSupport⟩ contDiff_const)
  simp only [inner_smul_right'] at hz
  refine ne_of_gt (integral_pos_of_integrable_nonneg_nonzero (x := a) hc'
    (hc'.integrable_of_hasCompactSupport b.hasCompactSupport.mul_right) ?_ ?_) hz
  · intro x
    by_cases hx : x ∈ Metric.ball a r
    · exact mul_nonneg b.nonneg (hball hx).le
    · simp only [Pi.mul_apply, Pi.zero_apply, b.zero_of_le_dist (le_of_not_gt hx), zero_mul, le_refl]
  · exact mul_ne_zero (ne_of_gt (b.pos_of_mem_ball (Metric.mem_ball_self hr)))
      (ne_of_gt hp)
