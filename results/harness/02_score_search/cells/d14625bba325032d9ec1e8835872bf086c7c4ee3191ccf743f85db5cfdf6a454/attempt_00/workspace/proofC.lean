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
  obtain ⟨r, hr, hball⟩ := Metric.mem_nhds_iff.mp
    ((isOpen_lt continuous_const hc).mem_nhds hp)
  let b : ContDiffBump x := ⟨r / 2, r, half_pos hr, half_lt_self hr⟩
  have hz := hg (fun y => b y • f x)
    (IsTestFunction.smul_right ⟨b.contDiff, b.hasCompactSupport⟩ contDiff_const)
  simp only [inner_smul_right'] at hz
  apply hz.symm.not_lt
  exact
    (b.continuous.mul hc).integral_pos_of_hasCompactSupport_nonneg_nonzero
      b.hasCompactSupport.mul_right (fun y => by
        by_cases hy : y ∈ Metric.ball x r
        · exact mul_nonneg b.nonneg (hball hy).le
        · change 0 ≤ b y * _
          rw [b.zero_of_le_dist (le_of_not_gt hy), zero_mul])
      (mul_ne_zero (b.pos_of_mem_ball (Metric.mem_ball_self hr)).ne' hp.ne')
