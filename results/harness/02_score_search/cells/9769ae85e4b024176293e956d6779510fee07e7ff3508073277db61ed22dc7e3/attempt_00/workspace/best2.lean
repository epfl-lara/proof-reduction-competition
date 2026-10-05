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
    LorentzCurrentDensity.currentDensity_apply_differentiable_time (hJ.differentiable (by simp)) x i
  have hg : (∑ j, ∂[j] (∂[i] (A.electricField 𝓕.c t · j)) x) =
      𝓕.ε₀⁻¹ * ∂[i] (J.chargeDensity 𝓕.c t ·) x := by
    have hc : ∀ j, ∂[j] (∂[i] (A.electricField 𝓕.c t · j)) =
        ∂[i] (∂[j] (A.electricField 𝓕.c t · j)) :=
      fun j => Space.deriv_commute _ (hEs j)
    simp only [hc]
    have he := congrArg (fun f : Space d → ℝ => ∂[i] f x)
      (funext fun y => ((isExtrema_iff_gauss_ampere_magneticFieldMatrix hA J hJ).mp h t y).1)
    change ∂[i] (fun y => ∑ j, ∂[j] (A.electricField 𝓕.c t · j) y) x = _ at he
    rw [Space.deriv_eq_fderiv_basis,
      fderiv_fun_sum (fun j _ => (hEd j j).differentiableAt)] at he
    simp only [FunLike.coe_sum, Finset.sum_apply, ← Space.deriv_eq_fderiv_basis] at he
    rw [he]
    simp only [div_eq_mul_inv]
    rw [Space.deriv_eq_fderiv_basis, fderiv_mul_const
      (LorentzCurrentDensity.chargeDensity_differentiable_space
        (hJ.differentiable (by simp)) t).differentiableAt]
    simp [← Space.deriv_eq_fderiv_basis, mul_comm]
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
      simp only [one_div, mul_inv_rev, FunLike.coe_sub, Pi.sub_apply]
      rw [fderiv_const_mul (Differentiable.fun_sum fun j _ => hBt j).differentiableAt]
      rw [fderiv_const_mul hJt.differentiableAt]
      simp [Time.deriv_eq]
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
      simp_rw [Finset.sum_apply, Space.time_deriv_comm_space_deriv
        (magneticFieldMatrix_contDiff _ (hA.of_le (right_eq_inf.mp rfl)) _),
        time_deriv_magneticFieldMatrix _ (hA.of_le (ENat.LEInfty.out))]
    _ = _ := by
      simp only [Finset.sum_apply]
      have hs : ∀ j, ∂[j] (fun y => ∂[j] (A.electricField 𝓕.c t · i) y -
          ∂[i] (A.electricField 𝓕.c t · j) y) x =
          ∂[j] (∂[j] (A.electricField 𝓕.c t · i)) x -
          ∂[j] (∂[i] (A.electricField 𝓕.c t · j)) x :=
        fun j => congrFun (Space.deriv_sub _ _ (hEd i j) (hEd j i)) x
      simp only [hs]
      simp only [Finset.sum_sub_distrib, mul_sub, hg]
      simp [FreeSpace.c_sq]
      field_simp
