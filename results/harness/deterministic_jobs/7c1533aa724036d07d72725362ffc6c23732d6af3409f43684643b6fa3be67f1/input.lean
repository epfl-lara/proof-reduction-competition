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
  obtain ⟨φ, hs, hk, hd, hn, hφ⟩ := exists_contDiff_tsupport_subset (n := ⊤)
    ((isOpen_lt continuous_const hc).mem_nhds hp)
  have hz := hg (fun y => φ y • f x)
    (IsTestFunction.smul_right ⟨hd, hk⟩ contDiff_const)
  simp only [inner_smul_right'] at hz
  apply hz.not_gt
  refine (hd.continuous.fun_mul hc).integral_pos_of_hasCompactSupport_nonneg_nonzero
    hk.mul_right (fun y => ?_) (x := x) ?_
  · by_cases hy : φ y = 0
    · rw [Pi.zero_apply, hy, zero_mul]
    · exact mul_nonneg (hn ⟨y, rfl⟩).1 (hs (subset_tsupport _ hy)).le
  · rw [hφ, one_mul]
    exact hp.ne'