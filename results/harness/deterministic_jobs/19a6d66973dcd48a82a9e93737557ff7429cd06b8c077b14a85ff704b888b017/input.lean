lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  funext x
  change f x = 0
  by_contra hx
  have hp : 0 < ⟪f x, f x⟫_ℝ :=
    real_inner_self_nonneg'.lt_of_ne' (mt inner_self_eq_zero'.mp hx)
  have hc := Continuous.inner' (𝕜 := ℝ) f (fun _ => f x) hf continuous_const
  obtain ⟨r, hr, hball⟩ := Metric.isOpen_iff.mp (isOpen_lt continuous_const hc) x hp
  let φ : ContDiffBump x := ⟨r / 2, r, half_pos hr, half_lt_self hr⟩
  have hn : ∀ y, 0 ≤ φ y * ⟪f y, f x⟫_ℝ := by
    intro y
    by_cases hy : y ∈ Metric.ball x r
    · exact mul_nonneg φ.nonneg (hball hy).le
    · rw [φ.zero_of_le_dist (le_of_not_gt hy), zero_mul]
  have hpos : 0 < ∫ y, φ y * ⟪f y, f x⟫_ℝ ∂μ :=
    (φ.continuous.mul hc).integral_pos_of_hasCompactSupport_nonneg_nonzero
      φ.hasCompactSupport.mul_right hn
      (mul_ne_zero (φ.pos_of_mem_ball (Metric.mem_ball_self hr)).ne' hp.ne')
  have hz := hg (fun y => φ y • f x)
    (IsTestFunction.smul_right ⟨φ.contDiff, φ.hasCompactSupport⟩ contDiff_const)
  simp only [inner_smul_right'] at hz
  exact hpos.ne' hz