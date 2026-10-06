lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  by_contra h₀
  obtain ⟨x₀, hx0⟩ := Function.ne_iff.mp h₀
  have hpos :=
    lt_of_le_of_ne real_inner_self_nonneg' (Ne.symm (mt inner_self_eq_zero'.1 hx0))
  have hinner_cont := Continuous.inner' (𝕜 := ℝ) _ (fun _ => f x₀) hf continuous_const
  obtain ⟨δ, hδ_pos, inner_pos_V⟩ :=
    Metric.isOpen_iff.mp (isOpen_lt continuous_const hinner_cont) x₀ hpos
  let φ : ContDiffBump x₀ := ⟨_, δ, half_pos hδ_pos, half_lt_self hδ_pos⟩
  have hg_test :=
    IsTestFunction.smul_right ⟨φ.contDiff, φ.hasCompactSupport⟩ (contDiff_const (c := f x₀))
  have h_nonneg : 0 ≤ fun x => φ x * ⟪f x, f x₀⟫_ℝ := by
    intro x
    by_cases hx : φ x = 0
    · simp [hx]
    · exact mul_nonneg φ.nonneg (inner_pos_V (φ.support_eq.subset hx)).le
  have integral_pos :=
    Continuous.integral_pos_of_hasCompactSupport_nonneg_nonzero (μ := μ)
      (φ.continuous.mul hinner_cont)
      φ.hasCompactSupport.mul_right
      h_nonneg
      (mul_pos (φ.pos_of_mem_ball (Metric.mem_ball_self hδ_pos)) hpos).ne'
  exact integral_pos.ne' (by simpa only [inner_smul_right', Pi.mul_apply] using hg _ hg_test)