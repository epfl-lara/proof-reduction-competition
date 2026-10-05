lemma fundamental_theorem_of_variational_calculus' {f : Y → V}
    (μ : Measure Y) [IsFiniteMeasureOnCompacts μ] [μ.IsOpenPosMeasure]
    [OpensMeasurableSpace Y]
    (hf : Continuous f) (hg : ∀ g, IsTestFunction g → ∫ x, ⟪f x, g x⟫_ℝ ∂μ = 0) :
    f = 0 := by
  -- assume ¬(f = 0)
    rw [funext_iff]; by_contra h₀
    obtain ⟨x₀, hx0⟩ := not_forall.1 h₀
    simp at hx0 -- hx0 : f x₀ ≠ 0

  -- [1] Proof that `f` is continuous at `x₀`.
  -- Embed into the true IP-space `WithLp 2 V`.
  -- Continuity of the scalar product itself gives positivity nearby.
    let q : Y → ℝ := fun x => ⟪f x, f x₀⟫_ℝ
    have hinner_cont : Continuous (fun x => ⟪f x, f x₀⟫_ℝ) :=
      Continuous.inner' (f : Y → V) (fun _ => f x₀) hf continuous_const
    have hq : ContinuousAt q x₀ := hinner_cont.continuousAt
    have hself : 0 < q x₀ := by
      have hnn : 0 ≤ q x₀ := by
        simpa [q] using (real_inner_self_nonneg' (F := V) (x := f x₀))
      have hne : q x₀ ≠ 0 := by
        intro h
        exact hx0 ((inner_self_eq_zero' (𝕜 := ℝ)).mp (by simpa [q] using h))
      exact lt_of_le_of_ne hnn (Ne.symm hne)
    obtain ⟨δ₂, hδ₂_pos, hδ₂⟩ :=
      Metric.continuousAt_iff.mp hq (q x₀ / 2) (by linarith)
    have inner_pos₂ : ∀ x (hx : x ∈ Metric.ball x₀ δ₂), 0 < q x := by
      intro x hx
      have hd := hδ₂ (Metric.mem_ball.mp hx)
      have : |q x - q x₀| < q x₀ / 2 := by simpa [Real.dist_eq] using hd
      have := abs_lt.mp this
      linarith
  -- [3] `g` construction using bump function.
    haveI : HasContDiffBump Y := hasContDiffBump_of_innerProductSpace Y
    let φ1 : ContDiffBump x₀ := ⟨δ₂ / 4, δ₂ / 2, by positivity, by linarith⟩
    let φ : Y → ℝ := φ1.toFun
    have hφ_testfun : IsTestFunction φ := ⟨φ1.contDiff, φ1.hasCompactSupport⟩
    have hφ_non_neg : ∀ x ∈ Function.support φ, 0 ≤ φ x := fun x _ => φ1.nonneg
    have hφ_support_subset : Function.support φ ⊆ Metric.ball x₀ (δ₂/2) := by
      change Function.support φ1.toFun ⊆ Metric.ball x₀ (δ₂/2)
      rw [ContDiffBump.support_eq]
    have hφ_pos_inner : ∀ x ∈ Metric.closedBall x₀ (δ₂/4), 0 < φ x := by
      intro x hx
      apply φ1.pos_of_mem_ball
      exact Metric.mem_ball.mpr
        (lt_of_le_of_lt hx (by show δ₂ / 4 < δ₂ / 2; linarith))
    have key_integral : ∫ x, φ x * ⟪f x, f x₀⟫_ℝ ∂μ = 0 := by
      simpa only [inner_smul_right'] using
        hg (fun x => φ x • f x₀) (IsTestFunction.smul_right hφ_testfun contDiff_const)

  -- [4.2] 0 < ∫ x, φ x * ⟪f x, f x₀⟫_ℝ ∂μ. Sketch: on the support of φ (which is contained in
  -- B(x₀, δ/2) ⊆ B(x₀, δ)), we have ⟪f x, f x₀⟫ > ‖f x₀‖²/2 > 0 by our choice of δ.
  -- Since φ is nonnegative on its support and positive somewhere, this gives the contradiction.

  -- [4.2.1] Integrability of the integrand: `integrable_prod` .
    have support_subset : Function.support φ ⊆ Metric.ball x₀ δ₂ :=
      hφ_support_subset.trans (Metric.ball_subset_ball (by linarith))
    have supp_subset2 : Function.support (fun x => φ x * ⟪f x, f x₀⟫_ℝ) ⊆ Function.support φ := by simp
    have integrable_prod :
      Integrable (fun x => φ x * ⟪f x, f x₀⟫_ℝ) μ :=
    -- (i) build a `HasCompactSupport` witness for the product
      (Continuous.mul hφ_testfun.smooth.continuous hinner_cont).integrable_of_hasCompactSupport
        (hφ_testfun.supp.mono supp_subset2)

  -- [4.2.2] Nonnegativity everywhere (`h_nonneg`)
    have h_nonneg : ∀ x, 0 ≤ φ x * ⟪f x, f x₀⟫_ℝ := by
      intro x
      by_cases hx : x ∈ Function.support φ
      · -- on the support, φ ≥ 0 and ⟪f x, f x₀⟫ > 0
        exact mul_nonneg (hφ_non_neg x hx) (inner_pos₂ x (support_subset hx)).le
      · -- off the support, φ x = 0 so the product is 0
        simp [Function.notMem_support.mp hx]

  -- [4.2.3] That closed ball has positive measure, and is contained in the support
    -- every nonempty open set has positive measure
    have hμ_ball : 0 < μ (Metric.ball x₀ (δ₂/4)) :=
      Metric.isOpen_ball.measure_pos μ (Metric.nonempty_ball.mpr (by positivity))
    have ball_subset_support :
        Metric.ball x₀ (δ₂/4)
          ⊆ Function.support (fun x => φ x * ⟪f x, f x₀⟫_ℝ) := by
        intro x hx
        have hφx := hφ_pos_inner x (Metric.ball_subset_closedBall hx)
        have hin : 0 < ⟪f x, f x₀⟫_ℝ :=
          inner_pos₂ x (Metric.ball_subset_ball (by linarith) hx)
        simp only [Function.support_mul, Set.mem_inter_iff, Function.mem_support]
        constructor
        · linarith
        · linarith

  -- [4.2.4] putting everything together: positivity contradicts `key_integral : ∫ ... = 0`
    have integral_pos : 0 < ∫ x, φ x * ⟪f x, f x₀⟫_ℝ ∂μ :=
      (integral_pos_iff_support_of_nonneg h_nonneg integrable_prod).mpr
        (lt_of_lt_of_le hμ_ball
          (measure_mono ball_subset_support))
    linarith