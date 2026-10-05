lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  funext a
  by_contra ha
  have hc : Continuous (fun x => ⟪f x, f a⟫_ℝ) := Continuous.inner' f (fun _ => f a) hf continuous_const
  have hp : 0 < ⟪f a, f a⟫_ℝ :=
    lt_of_le_of_ne real_inner_self_nonneg' (Ne.symm (mt inner_self_eq_zero'.mp ha))
  obtain ⟨r, hr, hball⟩ := Metric.isOpen_iff.mp (isOpen_lt continuous_const hc) a hp
  let φ : ContDiffBump a := ⟨r / 2, r, half_pos hr, half_lt_self hr⟩
  have ht : IsTestFunction (fun x => φ x • f a) :=
    IsTestFunction.smul_right ⟨φ.contDiff, φ.hasCompactSupport⟩ contDiff_const
  have hcont := φ.continuous.mul hc
  have hint := hcont.integrable_of_hasCompactSupport
    φ.hasCompactSupport.mul_right (μ := μ)
  have hn : ∀ x, 0 ≤ φ x * ⟪f x, f a⟫_ℝ := by
    intro x
    by_cases hx : x ∈ Function.support φ
    · exact mul_nonneg φ.nonneg (hball (φ.support_eq ▸ hx)).le
    · simp only [Function.notMem_support.mp hx, zero_mul, le_refl]
  have hpos := integral_pos_of_integrable_nonneg_nonzero hcont hint hn
    (mul_ne_zero (φ.pos_of_mem_ball (Metric.mem_ball_self hr)).ne' hp.ne')
  have hz := hg _ ht
  simp only [inner_smul_right'] at hz
  exact (ne_of_gt hpos) hz
