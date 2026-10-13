lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  ext x
  apply (inner_self_eq_zero' (𝕜 := ℝ)).mp
  refine le_antisymm ?_ real_inner_self_nonneg'
  by_contra! hp
  have hc := Continuous.inner' (𝕜 := ℝ) f (fun _ => f x) hf continuous_const
  obtain ⟨φ, hsub, hcomp, hsmooth, hrange, heq⟩ :=
    exists_contDiff_tsupport_subset (hc.continuousAt (Ioi_mem_nhds hp))
  refine ((hsmooth.continuous.fun_mul hc).integral_pos_of_hasCompactSupport_nonneg_nonzero
    hcomp.mul_right ?_ (mul_ne_zero (heq.trans_ne one_ne_zero) hp.ne')).ne' (by
    simpa only [inner_smul_right'] using
      hg _
        (IsTestFunction.smul_right ⟨hsmooth, hcomp⟩ (contDiff_const (c := f x))))
  intro y
  by_cases hy : y ∈ tsupport φ
  · exact mul_nonneg (hrange ⟨y, rfl⟩).1 (le_of_lt (hsub hy))
  · simp [image_eq_zero_of_notMem_tsupport hy]