lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  funext x₀
  change f x₀ = 0
  by_contra hx₀
  have hcont : Continuous (fun x => ⟪f x, f x₀⟫_ℝ) :=
    Continuous.inner' _ _ hf continuous_const
  have hpos : 0 < ⟪f x₀, f x₀⟫_ℝ :=
    (real_inner_self_nonneg' (x := f x₀)).lt_of_ne'
      ((inner_self_eq_zero' (𝕜 := ℝ)).not.mpr hx₀)
  obtain ⟨r, hr, hball⟩ :=
    Metric.isOpen_iff.mp (isOpen_lt continuous_const hcont) x₀ hpos
  let φ : ContDiffBump x₀ := ⟨r / 2, r, half_pos hr, half_lt_self hr⟩
  have hφ : IsTestFunction (φ : Y → ℝ) := ⟨φ.contDiff, φ.hasCompactSupport⟩
  have hzero := hg (fun x => φ x • f x₀) (hφ.smul_right contDiff_const)
  simp only [inner_smul_right'] at hzero
  have hnonneg : ∀ x, 0 ≤ φ x * ⟪f x, f x₀⟫_ℝ := by
    intro x
    by_cases hx : x ∈ Metric.ball x₀ r
    · exact mul_nonneg φ.nonneg (hball hx).le
    · rw [φ.zero_of_le_dist (le_of_not_gt hx), zero_mul]
  have hprod := (φ.continuous.mul hcont).integral_pos_of_hasCompactSupport_nonneg_nonzero
    (μ := μ) φ.hasCompactSupport.mul_right hnonneg
    (mul_ne_zero (φ.pos_of_mem_ball (Metric.mem_ball_self hr)).ne' hpos.ne')
  exact hprod.ne' hzero
