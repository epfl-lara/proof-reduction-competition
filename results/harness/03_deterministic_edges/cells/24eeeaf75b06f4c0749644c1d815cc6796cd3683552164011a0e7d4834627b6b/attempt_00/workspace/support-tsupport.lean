lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  funext x
  apply (inner_self_eq_zero' (𝕜 := ℝ)).mp
  refine le_antisymm (le_of_not_gt fun hp => ?_) real_inner_self_nonneg'
  have hc := Continuous.inner' (𝕜 := ℝ) f (fun _ => f x) hf continuous_const
  obtain ⟨φ, hs, hk, hd, hn, hxφ⟩ := exists_contDiff_tsupport_subset (n := ⊤)
    (Filter.Tendsto.eventually_const_lt hp hc.continuousAt)
  have hcont := hd.continuous.mul hc
  apply (hg (fun y => φ y • f x)
    (IsTestFunction.smul_right ⟨hd, hk⟩ contDiff_const)).not_gt
  simp only [inner_smul_right']
  refine integral_pos_of_integrable_nonneg_nonzero hcont
    (hcont.integrable_of_hasCompactSupport hk.mul_right) ?_
    (mul_ne_zero (hxφ.trans_ne one_ne_zero) hp.ne')
  intro y
  by_cases hy : y ∈ tsupport φ
  · exact mul_nonneg (hn (Set.mem_range_self y)).1 (hs hy).le
  · simp [image_eq_zero_of_notMem_tsupport hy]
