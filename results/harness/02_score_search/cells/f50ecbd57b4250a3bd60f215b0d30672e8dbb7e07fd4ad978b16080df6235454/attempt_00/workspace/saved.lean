lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  funext x
  by_contra hx
  have hp : 0 < ⟪f x, f x⟫_ℝ :=
    (real_inner_self_pos (x := toL2 ℝ (f x))).2 (fun h => hx (congrArg (fromL2 ℝ) h))
  have hc := Continuous.inner' (𝕜 := ℝ) f (fun _ => f x) hf continuous_const
  obtain ⟨r, hr, hball⟩ := Metric.eventually_nhds_iff_ball.mp
    (hc.continuousAt.eventually (lt_mem_nhds hp))
  let b : ContDiffBump x := ⟨r / 2, r, half_pos hr, half_lt_self hr⟩
  have hn : ∀ y, 0 ≤ b y * ⟪f y, f x⟫_ℝ := by
    intro y
    by_cases hy : y ∈ Metric.ball x r
    · exact mul_nonneg b.nonneg (hball y hy).le
    · rw [b.zero_of_le_dist (le_of_not_gt hy), zero_mul]
  have hi := (b.continuous.mul hc).integral_pos_of_hasCompactSupport_nonneg_nonzero
    (μ := μ) b.hasCompactSupport.mul_right hn
    (mul_pos (b.pos_of_mem_ball (Metric.mem_ball_self hr)) hp).ne'
  have hz := hg (fun y => b y • f x)
    (IsTestFunction.smul_right ⟨b.contDiff, b.hasCompactSupport⟩ contDiff_const)
  simp only [inner_smul_right'] at hz
  exact hi.ne' hz
