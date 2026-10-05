lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  funext x
  by_contra hx
  have hc :=
    Continuous.inner' (𝕜 := ℝ) f (fun _ => f x) hf continuous_const
  have hp :=
    lt_of_le_of_ne' real_inner_self_nonneg' (inner_self_eq_zero'.not.mpr hx)
  obtain ⟨φ, hs, hcomp, hdiff, hrange, hφx⟩ :=
    exists_contDiff_tsupport_subset (n := ⊤) ((isOpen_Ioi.preimage hc).mem_nhds hp)
  have hpositive :=
    (hdiff.continuous.mul hc).integral_pos_of_hasCompactSupport_nonneg_nonzero (μ := μ)
      hcomp.mul_right (fun y => by
        by_cases hy : φ y = 0
        · simp [hy]
        · exact mul_nonneg (hrange ⟨y, rfl⟩).1 (hs (subset_tsupport φ hy)).le)
      (mul_ne_zero (hφx.trans_ne one_ne_zero) hp.ne')
  apply hpositive.ne'
  simpa only [inner_smul_right', Pi.mul_apply] using hg (fun y => φ y • f x)
    (IsTestFunction.smul_right ⟨hdiff, hcomp⟩ contDiff_const)
