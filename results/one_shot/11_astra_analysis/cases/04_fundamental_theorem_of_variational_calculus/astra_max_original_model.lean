lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  funext x₀
  change f x₀ = 0
  by_contra hx₀
  have hinner : Continuous (fun x => ⟪f x, f x₀⟫_ℝ) :=
    Continuous.inner' _ _ hf continuous_const
  have hpos : 0 < ⟪f x₀, f x₀⟫_ℝ :=
    lt_of_le_of_ne real_inner_self_nonneg'
      (fun h => hx₀ (inner_self_eq_zero'.mp h.symm))
  obtain ⟨r, hr, hball⟩ := Metric.eventually_nhds_iff.mp
    (continuousAt_const.eventually_lt hinner.continuousAt hpos)
  let φ : ContDiffBump x₀ := ⟨r / 2, r, half_pos hr, half_lt_self hr⟩
  have hc : Continuous (fun x => φ x * ⟪f x, f x₀⟫_ℝ) := φ.continuous.mul hinner
  have hn : ∀ x, 0 ≤ φ x * ⟪f x, f x₀⟫_ℝ := by
    intro x
    by_cases hx : dist x x₀ < r
    · exact mul_nonneg φ.nonneg (hball hx).le
    · rw [φ.zero_of_le_dist (le_of_not_gt hx), zero_mul]
  have hp := integral_pos_of_integrable_nonneg_nonzero hc
    (hc.integrable_of_hasCompactSupport φ.hasCompactSupport.mul_right (μ := μ)) hn
    (mul_pos (φ.pos_of_mem_ball (Metric.mem_ball_self hr)) hpos).ne'
  have hz := hg (fun x => φ x • f x₀)
    (IsTestFunction.smul_right ⟨φ.contDiff, φ.hasCompactSupport⟩ contDiff_const)
  simp only [inner_smul_right'] at hz
  exact hp.ne' hz
