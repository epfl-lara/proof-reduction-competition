lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  funext x
  apply (inner_self_eq_zero' (𝕜 := ℝ)).mp
  by_contra hx
  have hc := hf.inner' (𝕜 := ℝ) f (fun _ => f x) continuous_const
  obtain ⟨φ, hs, hcomp, hsmooth, hnonneg, hxone⟩ :=
    exists_contDiff_tsupport_subset (hc.continuousAt.eventually_const_le (real_inner_self_nonneg'.lt_of_ne' hx))
  refine (ne_of_gt ?_) (hg _ (IsTestFunction.smul_right
    ⟨hsmooth, hcomp⟩ (contDiff_const (c := f x))))
  simp only [inner_smul_right']
  apply (hsmooth.continuous.fun_mul hc).integral_pos_of_hasCompactSupport_nonneg_nonzero hcomp.mul_right
  · intro y
    rcases (hnonneg ⟨y, rfl⟩).1.eq_or_lt with hy | hy
    · simp [← hy]
    · apply mul_nonneg hy.le
      exact hs (subset_tsupport φ hy.ne')
  · exact mul_ne_zero (hxone.trans_ne one_ne_zero) hx