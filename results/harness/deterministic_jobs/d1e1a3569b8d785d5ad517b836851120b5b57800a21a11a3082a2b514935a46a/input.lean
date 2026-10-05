lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  funext x
  by_contra hx
  have hp : 0 < ⟪f x, f x⟫_ℝ :=
    real_inner_self_nonneg'.lt_of_ne' (mt inner_self_eq_zero'.mp hx)
  have hc := Continuous.inner' (𝕜 := ℝ) f (fun _ => f x) hf continuous_const
  obtain ⟨r, hr, hball⟩ := Metric.isOpen_iff.mp (isOpen_lt continuous_const hc) x hp
  let φ : ContDiffBump x := ⟨r / 2, r, half_pos hr, half_lt_self hr⟩
  refine ((φ.continuous.mul hc).integral_pos_of_hasCompactSupport_nonneg_nonzero
    (μ := μ) φ.hasCompactSupport.mul_right (fun y => ?_)
    (mul_ne_zero (φ.pos_of_mem_ball (Metric.mem_ball_self hr)).ne' hp.ne')).ne' ?_
  · by_cases hy : y ∈ Metric.ball x r
    · exact mul_nonneg φ.nonneg (hball hy).le
    · simp only [Pi.mul_apply, Pi.zero_apply, φ.zero_of_le_dist (le_of_not_gt hy), zero_mul, le_refl]
  · simpa only [Pi.mul_apply, inner_smul_right'] using hg (fun y => φ y • f x)
      ⟨φ.contDiff.smul contDiff_const, φ.hasCompactSupport.smul_right⟩