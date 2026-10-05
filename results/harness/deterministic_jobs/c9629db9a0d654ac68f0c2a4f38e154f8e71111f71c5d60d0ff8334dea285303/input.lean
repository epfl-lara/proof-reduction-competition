lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  rw [funext_iff]
  by_contra! h
  obtain ⟨x₀, hx0⟩ := h
  let q : Y → ℝ := fun x => ⟪f x, f x₀⟫_ℝ
  have hq0 : 0 < q x₀ := by
    dsimp [q]
    exact lt_of_le_of_ne real_inner_self_nonneg'
      (Ne.symm (by simpa [inner_self_eq_zero'] using hx0))
  have hcont : Continuous q :=
    Continuous.inner' f (fun _ => f x₀) hf continuous_const
  obtain ⟨δ, hδpos, hδ⟩ :=
    Metric.continuousAt_iff.mp hcont.continuousAt (q x₀ / 2) (by positivity)
  have hpos : ∀ x ∈ Metric.ball x₀ δ, 0 < q x := by
    intro x hx
    have hc := hδ (Metric.mem_ball.mp hx)
    rw [Real.dist_eq] at hc
    dsimp [q]
    linarith only [hq0, (abs_lt.mp hc).1]
  haveI : HasContDiffBump Y := hasContDiffBump_of_innerProductSpace Y
  let φ1 : ContDiffBump x₀ := ⟨δ / 2, δ, by positivity, by linarith⟩
  let φ : Y → ℝ := φ1.toFun
  have hφ_testfun : IsTestFunction φ := ⟨φ1.contDiff, φ1.hasCompactSupport⟩
  have hφ_support_subset : Function.support φ ⊆ Metric.ball x₀ δ := by
    change Function.support φ1.toFun ⊆ _
    rw [ContDiffBump.support_eq]
  have key_integral := hg (fun x => φ x • f x₀)
    (IsTestFunction.smul_right hφ_testfun contDiff_const)
  simp only [inner_smul_right'] at key_integral
  have integrable_prod : Integrable (fun x => φ x * q x) μ :=
    (Continuous.mul hφ_testfun.smooth.continuous hcont).integrable_of_hasCompactSupport
      hφ_testfun.supp.mul_right
  have h_nonneg : ∀ x, 0 ≤ φ x * q x := by
    intro x
    by_cases hx : x ∈ Function.support φ
    · exact mul_nonneg φ1.nonneg (hpos x (hφ_support_subset hx)).le
    · simp [Function.notMem_support.mp hx]
  have hμ : 0 < μ (Metric.ball x₀ (δ/2)) :=
    Metric.isOpen_ball.measure_pos μ (Metric.nonempty_ball.mpr (by positivity))
  have ball_subset_support : Metric.ball x₀ (δ/2) ⊆
      Function.support (fun x => φ x * q x) := by
    intro x hx
    have hxδ : x ∈ Metric.ball x₀ δ := Metric.ball_subset_ball (by linarith) hx
    simp only [Function.support_mul, Set.mem_inter_iff, Function.mem_support]
    exact ⟨ne_of_gt (φ1.pos_of_mem_ball hxδ), ne_of_gt (hpos x hxδ)⟩
  have integral_pos : 0 < ∫ x, φ x * q x ∂μ :=
    (integral_pos_iff_support_of_nonneg h_nonneg integrable_prod).mpr
      (lt_of_lt_of_le hμ (measure_mono ball_subset_support))
  change (∫ x, φ x * q x ∂μ) = 0 at key_integral
  simpa [key_integral] using integral_pos