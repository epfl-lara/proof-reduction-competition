lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  funext x
  by_contra hx
  have hp : 0 < ⟪f x, f x⟫_ℝ :=
    real_inner_self_nonneg'.lt_of_ne' (mt inner_self_eq_zero'.mp hx)
  have hc := Continuous.inner' (𝕜 := ℝ) f (fun _ => f x) hf continuous_const
  obtain ⟨b, hs, hk, hd, hn, hx⟩ := exists_contDiff_tsupport_subset (n := ⊤)
    ((isOpen_lt continuous_const hc).mem_nhds hp)
  have hz := hg (fun y => b y • f x)
    (IsTestFunction.smul_right ⟨hd, hk⟩ contDiff_const)
  simp only [inner_smul_right'] at hz
  apply hz.symm.not_lt
  exact (hd.continuous.mul hc).integral_pos_of_hasCompactSupport_nonneg_nonzero
    hk.mul_right (fun y => by
      by_cases hy : b y = 0
      · simp [hy]
      · exact mul_nonneg (hn (Set.mem_range_self y)).1 (hs (subset_tsupport b hy)).le)
    (mul_ne_zero (hx ▸ one_ne_zero) hp.ne')
