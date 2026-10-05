lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  funext x₀
  change f x₀ = 0
  by_contra hx₀
  have hpos : 0 < ⟪f x₀, f x₀⟫_ℝ :=
    (real_inner_self_nonneg' (x := f x₀)).lt_of_ne'
      (fun h => hx₀ (inner_self_eq_zero'.mp h))
  have hc : Continuous (fun x => ⟪f x, f x₀⟫_ℝ) :=
    Continuous.inner' f (fun _ => f x₀) hf continuous_const
  obtain ⟨δ, hδ, hball⟩ := Metric.isOpen_iff.mp
    (isOpen_lt continuous_const hc) x₀ hpos
  let φ : ContDiffBump x₀ := ⟨δ / 2, δ, half_pos hδ, half_lt_self hδ⟩
  have hprod := φ.continuous.mul hc
  have hnonneg : 0 ≤ (fun x => φ x * ⟪f x, f x₀⟫_ℝ) := by
    intro x
    by_cases hx : φ x = 0
    · simp only [hx, zero_mul, le_refl]
    · exact mul_nonneg φ.nonneg (hball (by rwa [← φ.support_eq])).le
  have hpositive := integral_pos_of_integrable_nonneg_nonzero hprod
    (hprod.integrable_of_hasCompactSupport φ.hasCompactSupport.mul_right) hnonneg
    (mul_ne_zero (φ.pos_of_mem_ball (Metric.mem_ball_self φ.rOut_pos)).ne' hpos.ne')
  apply hpositive.ne'
  simpa only [inner_smul_right'] using
    hg (fun x => φ x • f x₀)
      (IsTestFunction.smul_right ⟨φ.contDiff, φ.hasCompactSupport⟩ contDiff_const)
