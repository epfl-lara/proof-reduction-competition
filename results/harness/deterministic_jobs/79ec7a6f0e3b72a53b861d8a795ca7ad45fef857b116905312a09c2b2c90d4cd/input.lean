lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  funext a
  by_contra ha
  have hc : Continuous (fun x => ⟪f x, f a⟫_ℝ) := Continuous.inner' f (fun _ => f a) hf continuous_const
  have hp : 0 < ⟪f a, f a⟫_ℝ :=
    lt_of_le_of_ne real_inner_self_nonneg' (Ne.symm (inner_self_eq_zero'.not.mpr ha))
  obtain ⟨r, hr, hs⟩ := Metric.isOpen_iff.mp (isOpen_lt continuous_const hc) a hp
  let b : ContDiffBump a := ⟨r / 2, r, by positivity, by linarith⟩
  have hb : IsTestFunction (b : Y → ℝ) := ⟨b.contDiff, b.hasCompactSupport⟩
  have hz := hg (fun x => b x • f a) (hb.smul_right contDiff_const)
  simp only [inner_smul_right'] at hz
  have hpos : 0 < ∫ x, b x * ⟪f x, f a⟫_ℝ ∂μ := by
    refine (b.continuous.mul hc).integral_pos_of_hasCompactSupport_nonneg_nonzero
      (b.hasCompactSupport.mono (by simp)) ?_ (x := a) ?_
    · intro x
      by_cases hx : x ∈ Function.support (b : Y → ℝ)
      · exact mul_nonneg b.nonneg (le_of_lt (hs (by simpa [ContDiffBump.support_eq] using hx)))
      · simp [Function.notMem_support.mp hx]
    · exact ne_of_gt (mul_pos (b.pos_of_mem_ball (Metric.mem_ball_self hr)) hp)
  exact (ne_of_gt hpos) hz