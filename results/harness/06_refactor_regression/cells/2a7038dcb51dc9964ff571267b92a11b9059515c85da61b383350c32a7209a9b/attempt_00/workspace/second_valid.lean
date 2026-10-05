lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  ext x
  by_contra hx
  have hc : Continuous (fun y => ⟪f y, f x⟫_ℝ) :=
    Continuous.inner' f (fun _ => f x) hf continuous_const
  have hp : 0 < ⟪f x, f x⟫_ℝ :=
    lt_of_le_of_ne' real_inner_self_nonneg' (inner_self_eq_zero'.not.mpr hx)
  obtain ⟨r, hr, hpos⟩ := Metric.isOpen_iff.mp (isOpen_Ioi.preimage hc) x hp
  let φ : ContDiffBump x := ⟨r / 2, r, half_pos hr, half_lt_self hr⟩
  have hn : ∀ y, 0 ≤ φ y * ⟪f y, f x⟫_ℝ := by
    intro y
    by_cases hy : y ∈ Function.support φ
    · exact mul_nonneg φ.nonneg (hpos (φ.support_eq ▸ hy)).le
    · rw [Function.notMem_support.mp hy, zero_mul]
  have hpositive : 0 < ∫ y, φ y * ⟪f y, f x⟫_ℝ ∂μ :=
    (φ.continuous.mul hc).integral_pos_of_hasCompactSupport_nonneg_nonzero
      φ.hasCompactSupport.mul_right hn
      (mul_ne_zero (φ.pos_of_mem_ball (Metric.mem_ball_self hr)).ne' hp.ne')
  have hz := hg (fun y => φ y • f x)
    (IsTestFunction.smul_right ⟨φ.contDiff, φ.hasCompactSupport⟩ contDiff_const)
  simp only [inner_smul_right'] at hz
  exact (ne_of_gt hpositive) hz
