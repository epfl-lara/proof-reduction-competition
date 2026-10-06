lemma time_deriv_time_deriv_electricField_of_isExtrema {A : ElectromagneticPotential d}
    {𝓕 : FreeSpace}
    (hA : ContDiff ℝ ∞ A) (J : LorentzCurrentDensity d)
    (hJ : ContDiff ℝ ∞ J) (h : IsExtrema 𝓕 A J)
    (t : Time) (x : Space d) (i : Fin d) :
    ∂ₜ (∂ₜ (A.electricField 𝓕.c · x i)) t =
      𝓕.c ^ 2 * ∑ j, (∂[j] (∂[j] (A.electricField 𝓕.c t · i)) x) -
      𝓕.c ^ 2 / 𝓕.ε₀ * ∂[i] (J.chargeDensity 𝓕.c t ·) x -
      𝓕.c ^ 2 * 𝓕.μ₀ * ∂ₜ (J.currentDensity 𝓕.c · x i) t := by
  have hEs : ∀ j, ContDiff ℝ 2 (fun y => A.electricField 𝓕.c t y j) :=
    fun j => electricField_apply_contDiff_space (i := j) (hA.of_le (right_eq_inf.mp rfl)) t
  have hEd : ∀ j k, Differentiable ℝ (∂[k] (fun y => A.electricField 𝓕.c t y j)) :=
    fun j k => Space.deriv_differentiable (hEs j) k
  have hBt : ∀ j, Differentiable ℝ
      (fun s => ∂[j] (fun y => A.magneticFieldMatrix 𝓕.c s y (j, i)) x) :=
    fun j => Space.space_deriv_differentiable_time (i := j)
      (magneticFieldMatrix_contDiff _ (hA.of_le (right_eq_inf.mp rfl)) (j, i)) x
  have hJt : Differentiable ℝ (fun s => J.currentDensity 𝓕.c s x i) :=
    LorentzCurrentDensity.currentDensity_apply_differentiable_time (hJ.differentiable (by decide)) x i
  calc _
    _= ∂ₜ (fun t =>
      1 / (𝓕.μ₀ * 𝓕.ε₀) * ∑ j, Space.deriv j (fun x => magneticFieldMatrix 𝓕.c A t x (j, i)) x -
      1 / 𝓕.ε₀ * LorentzCurrentDensity.currentDensity 𝓕.c J t x i) t := by
        conv_lhs =>
          enter [1]
          change fun t => ∂ₜ (A.electricField 𝓕.c · x i) t
          enter [t]
          rw [Time.deriv_euclid (electricField_differentiable_time
            (hA.of_le (right_eq_inf.mp rfl)) _),
            time_deriv_electricField_of_isExtrema hA J hJ h]
    _ = 1 / (𝓕.μ₀ * 𝓕.ε₀) * ∂ₜ (fun t => ∑ j, ∂[j] (A.magneticFieldMatrix 𝓕.c t · (j, i)) x) t -
      1 / 𝓕.ε₀ * ∂ₜ (J.currentDensity 𝓕.c · x i) t := by
      rw [Time.deriv_eq]
      rw [fderiv_fun_sub]
      simp only
      rw [fderiv_const_mul (Differentiable.fun_sum fun j _ => hBt j).differentiableAt]
      rw [fderiv_const_mul hJt.differentiableAt]
      rfl
      · exact ((Differentiable.fun_sum fun j _ => hBt j).const_mul _).differentiableAt
      · exact hJt.differentiableAt.const_mul _
    _ = 1 / (𝓕.μ₀ * 𝓕.ε₀) * ((∑ j, ∂ₜ (fun t => ∂[j] (A.magneticFieldMatrix 𝓕.c t · (j, i)) x)) t) -
      1 / 𝓕.ε₀ * (∂ₜ (J.currentDensity 𝓕.c · x i) t) := by
      congr
      rw [Time.deriv_eq]
      rw [fderiv_fun_sum fun i _ => (hBt i).differentiableAt]
      simp only [FunLike.coe_sum, Finset.sum_apply]
      rfl
    _ = 1 / (𝓕.μ₀ * 𝓕.ε₀) *(∑ j, ∂[j] (fun x => ∂[j] (A.electricField 𝓕.c t · i) x -
        ∂[i] (A.electricField 𝓕.c t · j) x)) x -
        1 / 𝓕.ε₀ * ∂ₜ (J.currentDensity 𝓕.c · x i) t := by
      congr
      simp only [Finset.sum_apply]
      congr
      funext k
      rw [Space.time_deriv_comm_space_deriv (magneticFieldMatrix_contDiff _ (hA.of_le (right_eq_inf.mp rfl)) _)]
      congr
      funext x
      rw [time_deriv_magneticFieldMatrix _ (hA.of_le (ENat.LEInfty.out))]
    _ = (1 / (𝓕.μ₀ * 𝓕.ε₀) * ∑ j, (∂[j] (fun x => ∂[j] (A.electricField 𝓕.c t · i) x) x -
          ∂[j] (fun x => ∂[i] (A.electricField 𝓕.c t · j) x) x)) -
          1 / 𝓕.ε₀ * ∂ₜ (J.currentDensity 𝓕.c · x i) t := by
        congr
        simp only [Finset.sum_apply]
        congr
        funext j
        rw [Space.deriv_eq_fderiv_basis]
        rw [fderiv_fun_sub (hEd i j).differentiableAt (hEd j i).differentiableAt]
        rfl
    _ = 1 / (𝓕.μ₀ * 𝓕.ε₀) * ∑ j, (∂[j] (fun x => ∂[j] (A.electricField 𝓕.c t · i) x) x) -
          1 / (𝓕.μ₀ * 𝓕.ε₀) * ∑ j, (∂[j] (fun x => ∂[i] (A.electricField 𝓕.c t · j) x) x) -
          1 / 𝓕.ε₀ * ∂ₜ (J.currentDensity 𝓕.c · x i) t := by rw [Finset.sum_sub_distrib, mul_sub]
    _ = 1 / (𝓕.μ₀ * 𝓕.ε₀) * ∑ j, (∂[j] (fun x => ∂[j] (A.electricField 𝓕.c t · i) x) x) -
        1 / (𝓕.μ₀ * 𝓕.ε₀) * ∑ j, (∂[i] (fun x => ∂[j] (A.electricField 𝓕.c t · j) x) x) -
        1 / 𝓕.ε₀ * ∂ₜ (J.currentDensity 𝓕.c · x i) t := by
        congr
        funext j
        rw [Space.deriv_commute _ (hEs j)]
      _ = 1 / (𝓕.μ₀ * 𝓕.ε₀) * ∑ j, (∂[j] (fun x => ∂[j] (A.electricField 𝓕.c t · i) x) x) -
          1 / (𝓕.μ₀ * 𝓕.ε₀) * (∂[i] (fun x => ∑ j, ∂[j] (A.electricField 𝓕.c t · j) x) x) -
          1 / 𝓕.ε₀ * ∂ₜ (J.currentDensity 𝓕.c · x i) t := by
        congr
        rw [Space.deriv_eq_fderiv_basis]
        rw [fderiv_fun_sum (fun j _ => (hEd j j).differentiableAt)]
        rw [ContinuousLinearMap.sum_apply]
        rfl
      _ = 1 / (𝓕.μ₀ * 𝓕.ε₀) * ∑ j, (∂[j] (fun x => ∂[j] (A.electricField 𝓕.c t · i) x) x) -
          1 / (𝓕.μ₀ * 𝓕.ε₀) * (∂[i] (fun x => (∇ ⬝ (A.electricField 𝓕.c t)) x) x) -
          1 / 𝓕.ε₀ * ∂ₜ (J.currentDensity 𝓕.c · x i) t := by
        rfl
      _ = 𝓕.c ^ 2 * ∑ j, (∂[j] (∂[j] (A.electricField 𝓕.c t · i)) x) -
          𝓕.c ^ 2 / 𝓕.ε₀ * ∂[i] (J.chargeDensity 𝓕.c t ·) x -
          𝓕.c ^ 2 * 𝓕.μ₀ * ∂ₜ (J.currentDensity 𝓕.c · x i) t := by
        have hc : 1 / (𝓕.μ₀ * 𝓕.ε₀) = (𝓕.c : ℝ) ^ 2 := by rw [mul_comm, ← FreeSpace.c_sq]
        have hc3 : 1 / 𝓕.ε₀ = (𝓕.c : ℝ) ^ 2 * 𝓕.μ₀ := by
          rw [FreeSpace.c_sq, ← div_div, div_mul_cancel₀ _ 𝓕.μ₀_ne_zero]
        have hG : (fun x => (∇ ⬝ (A.electricField 𝓕.c t)) x) = fun x => (1 / 𝓕.ε₀) * J.chargeDensity 𝓕.c t x := by
          funext x
          rw [((isExtrema_iff_gauss_ampere_magneticFieldMatrix hA J hJ).mp h t x).1]
          ring
        have hJd : DifferentiableAt ℝ (fun x => J.chargeDensity 𝓕.c t x) x :=
          (LorentzCurrentDensity.chargeDensity_differentiable_space (hJ.differentiable (by decide)) t).differentiableAt
        have hT2 : ∂[i] (fun x => (∇ ⬝ (A.electricField 𝓕.c t)) x) x = (1 / 𝓕.ε₀) * ∂[i] (J.chargeDensity 𝓕.c t ·) x := by
          rw [hG, Space.deriv_eq_fderiv_basis, fderiv_const_mul hJd, ContinuousLinearMap.smul_apply, smul_eq_mul]
          rfl
        rw [hc, hc3, hT2]
        ring