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
  obtain ⟨r, hr, hpos⟩ := Metric.eventually_nhds_iff.mp
    (Filter.Tendsto.eventually_const_lt hp hc.continuousAt)
  let φ : ContDiffBump x := ⟨r / 2, r, half_pos hr, half_lt_self hr⟩
  have hcont := φ.continuous.mul hc
  have hzero := hg (fun y => φ y • f x)
    (IsTestFunction.smul_right ⟨φ.contDiff, φ.hasCompactSupport⟩ contDiff_const)
  simp only [inner_smul_right'] at hzero
  have hposint : 0 < ∫ y, φ y * ⟪f y, f x⟫_ℝ ∂μ := by
    apply integral_pos_of_integrable_nonneg_nonzero hcont
      (hcont.integrable_of_hasCompactSupport φ.hasCompactSupport.mul_right)
    · intro y
      by_cases hy : φ y = 0
      · simp only [Pi.zero_apply, Pi.mul_apply, hy, zero_mul, le_refl]
      · exact mul_nonneg φ.nonneg (hpos (by
          have : y ∈ Function.support φ := hy
          rwa [φ.support_eq] at this)).le
    · exact (mul_pos (φ.pos_of_mem_ball (Metric.mem_ball_self hr)) hp).ne'
  exact hposint.ne' hzero
