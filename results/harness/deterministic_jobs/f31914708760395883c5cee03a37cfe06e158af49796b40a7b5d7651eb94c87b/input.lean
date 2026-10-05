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
    let f₂ : Y → WithLp 2 V := toL2 ℝ ∘ f
    let x₂ := f₂ x₀
  -- x₂ ≠ 0 because `fromL2 (toL2 (f x₀)) = f x₀`
    have hx2 : x₂ ≠ 0 := by
      intro h; apply hx0; exact congrArg (fromL2 ℝ) h
  -- Continuity of the scalar product itself gives positivity nearby.
    let q : Y → ℝ := fun x => ⟪f₂ x, x₂⟫_ℝ
    have hq : ContinuousAt q x₀ := by
      change ContinuousAt (fun x => (⟪f₂ x, x₂⟫_ℝ : ℝ)) x₀
      exact (Continuous.inner ((toL2 ℝ).continuous.comp hf) continuous_const).continuousAt
    have hself : 0 < ⟪x₂, x₂⟫_ℝ := by
      rw [real_inner_self_eq_norm_sq]
      exact sq_pos_of_pos (norm_pos_iff.mpr hx2)
    obtain ⟨δ₂, hδ₂_pos, hδ₂⟩ :=
      Metric.continuousAt_iff.mp hq (⟪x₂, x₂⟫_ℝ / 2) (by linarith)
    have inner_pos₂ : ∀ x (hx : x ∈ Metric.ball x₀ δ₂), 0 < q x := by
      intro x hx
      have hd := hδ₂ (Metric.mem_ball.mp hx)
      have hcenter : q x₀ = ⟪x₂, x₂⟫_ℝ := rfl
      have : |q x - q x₀| < ⟪x₂, x₂⟫_ℝ / 2 := by simpa [Real.dist_eq] using hd
      rw [hcenter] at this
      have := abs_lt.mp this
      linarith
  -- pull `inner_pos₂` back to V via `fromL2`:
    have inner_pos_V : ∀ x ∈ Metric.ball x₀ δ₂, 0 < ⟪f x, f x₀⟫_ℝ := fun x hx => inner_pos₂ x hx
    -- now we have a genuine positive integrand on a set of positive measure.

  -- [3] `g` construction using bump function.
    have bump_exists : ∃ φ : Y → ℝ, IsTestFunction φ ∧ φ x₀ > 0 ∧
        (∀ x ∈ Function.support φ, 0 ≤ φ x) ∧
        Function.support φ ⊆ Metric.ball x₀ (δ₂/2) ∧
        (∀ x ∈ Metric.closedBall x₀ (δ₂/4), 0 < φ x) := by
        -- use `hasContDiffBump_of_innerProductSpace`, leveraging `[innerProductSpace Y]`
          haveI : HasContDiffBump Y := hasContDiffBump_of_innerProductSpace Y
          let φ1 : ContDiffBump x₀ :=
            ⟨δ₂ / 4, δ₂ / 2, by linarith, by linarith⟩
          refine ⟨φ1.toFun, ⟨φ1.contDiff, φ1.hasCompactSupport⟩,
            φ1.pos_of_mem_ball (Metric.mem_ball_self φ1.rOut_pos), fun x _ => φ1.nonneg,
            by rw [ContDiffBump.support_eq], fun x hx => φ1.pos_of_mem_ball ?_⟩
        -- the closed ball of radius `δ₂/4` lies in the open ball of radius `rOut = δ₂/2`
          
          exact Metric.mem_ball.mpr (lt_of_le_of_lt hx (by show δ₂ / 4 < δ₂ / 2; linarith))
    obtain ⟨φ, hφ_testfun, hφ_pos_x₀, hφ_non_neg, hφ_support_subset, hφ_pos_inner⟩ :=
      bump_exists
  -- Define test function g(x) = φ(x) * f(x₀)
    let g : Y → V := fun x => φ x • f x₀
  -- Show that g is a test function: `φ` is a test function and `f x₀` is smooth (constant)
    have hg_test : IsTestFunction g := IsTestFunction.smul_right hφ_testfun contDiff_const

  -- [4] Derive contradiction. First compute the integral ∫ ⟪f x, g x⟫
  -- [4.1] ∫ φ x * ⟪f x, f x₀⟫ = 0
    have key_integral := hg g hg_test
  -- linearity of inner product in the second argument turns the integrand into `φ x * ⟪f x, f x₀⟫`
    simp only [g, inner_smul_right'] at key_integral

  -- [4.2] 0 < ∫ x, φ x * ⟪f x, f x₀⟫_ℝ ∂μ. Sketch: on the support of φ (which is contained in
  -- B(x₀, δ/2) ⊆ B(x₀, δ)), we have ⟪f x, f x₀⟫ > ‖f x₀‖²/2 > 0 by our choice of δ.
  -- Since φ is nonnegative on its support and positive somewhere, this gives the contradiction.

  -- [4.2.1] Integrability of the integrand: `integrable_prod` .
    have support_subset : Function.support φ ⊆ Metric.ball x₀ δ₂ :=
      hφ_support_subset.trans (Metric.ball_subset_ball (by linarith))
    have supp_subset2 : Function.support (fun x => φ x * ⟪f x, f x₀⟫_ℝ) ⊆ Function.support φ := by simp
    have hinner_cont : Continuous (fun x => ⟪f x, f x₀⟫_ℝ) :=
      Continuous.inner' (f : Y → V) (fun _ => f x₀) hf continuous_const
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
        exact mul_nonneg (hφ_non_neg x hx) (inner_pos_V x (support_subset hx)).le
      · -- off the support, φ x = 0 so the product is 0
        simp [Function.notMem_support.mp hx]

  -- [4.2.3] That closed ball has positive measure, and is contained in the support
    -- every nonempty open set has positive measure
    have hμ_ball : 0 < μ (Metric.ball x₀ (δ₂/4)) :=
      Metric.isOpen_ball.measure_pos μ (Metric.nonempty_ball.mpr (by linarith))
    have closedBall_subset_support :
        Metric.closedBall x₀ (δ₂/4)
          ⊆ Function.support (fun x => φ x * ⟪f x, f x₀⟫_ℝ) := by
        intro x hx
        have hφx := hφ_pos_inner x hx
        have hin : 0 < ⟪f x, f x₀⟫_ℝ :=
          inner_pos_V x (Metric.closedBall_subset_ball (by linarith) hx)
        simp only [Function.support_mul, Set.mem_inter_iff, Function.mem_support]
        constructor
        · linarith
        · linarith

  -- [4.2.4] putting everything together: positivity contradicts `key_integral : ∫ ... = 0`
    have integral_pos : 0 < ∫ x, φ x * ⟪f x, f x₀⟫_ℝ ∂μ :=
      (integral_pos_iff_support_of_nonneg h_nonneg integrable_prod).mpr
        (lt_of_lt_of_le hμ_ball
          (measure_mono (Metric.ball_subset_closedBall.trans closedBall_subset_support)))
    linarith