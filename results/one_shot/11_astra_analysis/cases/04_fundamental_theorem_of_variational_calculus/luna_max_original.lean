lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  rw [funext_iff]
  by_contra h
  obtain ⟨x₀, hx₀⟩ := not_forall.mp h
  simp at hx₀
  let f₂ : Y → WithLp 2 V := toL2 ℝ ∘ f
  let x₂ := f₂ x₀
  have hx₂ : x₂ ≠ 0 := fun h => hx₀ (congrArg (fromL2 ℝ) h)
  have hc : ContinuousAt f₂ x₀ := ((toL2 ℝ).continuous.comp hf).continuousAt
  obtain ⟨δ, hδ, hball⟩ := Metric.continuousAt_iff.mp hc (‖x₂‖ / 2)
    (by simpa [half_pos] using (norm_pos_iff.mpr hx₂))
  have hi : ∀ x ∈ Metric.ball x₀ δ, 0 < (⟪f₂ x, x₂⟫_ℝ : ℝ) := by
    intro x hx
    have hclose : ‖f₂ x - x₂‖ < ‖x₂‖ / 2 := by
      simpa [dist_eq_norm, x₂] using hball hx
    have hs : ⟪x₂, x₂⟫_ℝ = ‖x₂‖ ^ 2 := real_inner_self_eq_norm_sq (x₂ : WithLp 2 V)
    have hcauchy : -(‖f₂ x - x₂‖ * ‖x₂‖) ≤ ⟪f₂ x - x₂, x₂⟫_ℝ :=
      neg_le_of_abs_le (abs_real_inner_le_norm _ _)
    have hp : 0 < ‖x₂‖ := norm_pos_iff.mpr hx₂
    have heq : ⟪f₂ x, x₂⟫_ℝ = ⟪x₂, x₂⟫_ℝ + ⟪f₂ x - x₂, x₂⟫_ℝ := by
      rw [← inner_add_left]
      simp
    nlinarith [heq, hcauchy, hs, hclose, hp, mul_lt_mul_of_pos_right hclose hp]
  have hip : ∀ x ∈ Metric.ball x₀ δ, 0 < ⟪f x, f x₀⟫_ℝ := fun x hx => hi x hx
  have hb : ∃ φ : Y → ℝ, IsTestFunction φ ∧
      (∀ x ∈ Function.support φ, 0 ≤ φ x) ∧
      Function.support φ ⊆ Metric.ball x₀ (δ / 2) ∧
      ∀ x ∈ Metric.closedBall x₀ (δ / 4), 0 < φ x := by
    haveI : HasContDiffBump Y := hasContDiffBump_of_innerProductSpace Y
    let b : ContDiffBump x₀ := ⟨δ / 4, δ / 2, by positivity, by linarith⟩
    refine ⟨b.toFun, ⟨b.contDiff, b.hasCompactSupport⟩, (fun x _ => b.nonneg),
      by rw [ContDiffBump.support_eq], fun x hx => b.pos_of_mem_ball ?_⟩
    rw [Metric.mem_closedBall] at hx
    exact Metric.mem_ball.mpr (lt_of_le_of_lt hx (by show δ / 4 < δ / 2; linarith))
  obtain ⟨φ, hφ, hφ_nonneg, hφ_support, hφ_pos⟩ := hb
  let g : Y → V := fun x => φ x • f x₀
  have hgt : IsTestFunction g := IsTestFunction.smul_right hφ contDiff_const
  have hzero := hg g hgt
  simp only [g, inner_smul_right'] at hzero
  have hsupport : Function.support φ ⊆ Metric.ball x₀ δ :=
    hφ_support.trans (Metric.ball_subset_ball (by linarith))
  have hinner : Continuous (fun x => ⟪f x, f x₀⟫_ℝ) :=
    Continuous.inner' (f : Y → V) (fun _ => f x₀) hf continuous_const
  have hint : Integrable (fun x => φ x * ⟪f x, f x₀⟫_ℝ) μ :=
    (Continuous.mul hφ.smooth.continuous hinner).integrable_of_hasCompactSupport
      hφ.supp.mul_right
  have hn : ∀ x, 0 ≤ φ x * ⟪f x, f x₀⟫_ℝ := by
    intro x
    by_cases hx : x ∈ Function.support φ
    · exact mul_nonneg (hφ_nonneg x hx) (hip x (hsupport hx)).le
    · simp [Function.notMem_support.mp hx]
  have hballpos : 0 < μ (Metric.ball x₀ (δ / 4)) :=
    Metric.isOpen_ball.measure_pos μ (Metric.nonempty_ball.mpr (by linarith))
  have hsupp : Metric.closedBall x₀ (δ / 4) ⊆
      Function.support (fun x => φ x * ⟪f x, f x₀⟫_ℝ) := by
    intro x hx
    have hp := hφ_pos x hx
    have hi := hip x (Metric.closedBall_subset_ball (by linarith) hx)
    simp only [Function.support_mul, Set.mem_inter_iff, Function.mem_support, ne_eq]
    exact ⟨by linarith, by linarith⟩
  have hpos : 0 < ∫ x, φ x * ⟪f x, f x₀⟫_ℝ ∂μ :=
    (integral_pos_iff_support_of_nonneg hn hint).mpr
      (lt_of_lt_of_le hballpos (measure_mono (Metric.ball_subset_closedBall.trans hsupp)))
  linarith
