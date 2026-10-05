lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  funext x₀
  by_contra hx
  have hc := hf.inner' (𝕜 := ℝ) _ (fun _ => f x₀) continuous_const
  obtain ⟨r, hr, hb⟩ := Metric.isOpen_iff.1 (isOpen_lt continuous_const hc) x₀
    (real_inner_self_nonneg'.lt_of_ne' (inner_self_eq_zero'.not.2 hx))
  let φ : ContDiffBump x₀ := ⟨_, _, half_pos hr, half_lt_self hr⟩
  have h1 := hg _ (IsTestFunction.smul_right ⟨φ.contDiff, φ.hasCompactSupport⟩ (contDiff_const (c := f x₀)))
  simp only [inner_smul_right'] at h1
  refine h1.not_gt ((φ.continuous.mul hc).integral_pos_of_hasCompactSupport_nonneg_nonzero
    φ.hasCompactSupport.mul_right (fun x => ?_)
    (mul_pos (φ.pos_of_mem_ball (Metric.mem_ball_self hr)) (hb (Metric.mem_ball_self hr))).ne')
  rcases lt_or_ge (dist x x₀) r with h | h
  · exact mul_nonneg φ.nonneg (hb h).le
  · exact (mul_eq_zero_of_left (φ.zero_of_le_dist h) _).ge