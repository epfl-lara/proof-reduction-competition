lemma time_deriv_time_deriv_electricField_of_isExtrema {A : ElectromagneticPotential d}
    {𝓕 : FreeSpace}
    (hA : ContDiff ℝ ∞ A) (J : LorentzCurrentDensity d)
    (hJ : ContDiff ℝ ∞ J) (h : IsExtrema 𝓕 A J)
    (t : Time) (x : Space d) (i : Fin d) :
    ∂ₜ (∂ₜ (A.electricField 𝓕.c · x i)) t =
      𝓕.c ^ 2 * ∑ j, (∂[j] (∂[j] (A.electricField 𝓕.c t · i)) x) -
      𝓕.c ^ 2 / 𝓕.ε₀ * ∂[i] (J.chargeDensity 𝓕.c t ·) x -
      𝓕.c ^ 2 * 𝓕.μ₀ * ∂ₜ (J.currentDensity 𝓕.c · x i) t := by
  have hA2 : ContDiff ℝ 2 A := hA.of_le ENat.LEInfty.out
  have hμ : 1 / (𝓕.μ₀ * 𝓕.ε₀) = 𝓕.c ^ 2 := by rw [mul_comm, FreeSpace.c_sq]
  have hε : 1 / 𝓕.ε₀ = 𝓕.c ^ 2 * 𝓕.μ₀ := by
    rw [div_eq_iff 𝓕.ε₀_ne_zero, FreeSpace.c_sq, mul_assoc, mul_comm 𝓕.μ₀ 𝓕.ε₀,
      div_mul_cancel₀ 1 (mul_ne_zero 𝓕.ε₀_ne_zero 𝓕.μ₀_ne_zero)]
  have hEs : ∀ j, ContDiff ℝ 2 (fun y => A.electricField 𝓕.c t y j) :=
    fun j => (electricField_apply_contDiff_space (i := j) hA t).of_le ENat.LEInfty.out
  have hEd : ∀ j k, Differentiable ℝ (∂[k] (A.electricField 𝓕.c t · j)) :=
    fun j k => Space.deriv_differentiable (hEs j) k
  have hBm : ∀ j, ContDiff ℝ 2 ↿(fun s y => A.magneticFieldMatrix 𝓕.c s y (j, i)) :=
    fun j => (magneticFieldMatrix_contDiff A hA (j, i)).of_le ENat.LEInfty.out
  have hBt : ∀ j, Differentiable ℝ (fun s => ∂[j] (A.magneticFieldMatrix 𝓕.c s · (j, i)) x) :=
    fun j => Space.space_deriv_differentiable_time (i := j) (hBm j) x
  have hK : Differentiable ℝ (fun s => J.currentDensity 𝓕.c s x i) :=
    LorentzCurrentDensity.currentDensity_apply_differentiable_time
      (hJ.differentiable (by decide)) x i
  have h1 : ∂ₜ (A.electricField 𝓕.c · x i) = fun s =>
      𝓕.c ^ 2 * ∑ j, ∂[j] (A.magneticFieldMatrix 𝓕.c s · (j, i)) x -
      𝓕.c ^ 2 * 𝓕.μ₀ * J.currentDensity 𝓕.c s x i := by
    funext s
    rw [Time.deriv_euclid (electricField_differentiable_time hA2 x) s,
      time_deriv_electricField_of_isExtrema hA J hJ h, hμ, hε]
  have h2 : ∂ₜ (fun s => 𝓕.c ^ 2 * ∑ j, ∂[j] (A.magneticFieldMatrix 𝓕.c s · (j, i)) x -
      𝓕.c ^ 2 * 𝓕.μ₀ * J.currentDensity 𝓕.c s x i) t
      = 𝓕.c ^ 2 * ∂ₜ (fun s => ∑ j, ∂[j] (A.magneticFieldMatrix 𝓕.c s · (j, i)) x) t -
      𝓕.c ^ 2 * 𝓕.μ₀ * ∂ₜ (fun s => J.currentDensity 𝓕.c s x i) t := by
    have hG : DifferentiableAt ℝ (fun s => ∑ j, ∂[j] (A.magneticFieldMatrix 𝓕.c s · (j, i)) x) t :=
      (Differentiable.fun_sum fun j _ => hBt j).differentiableAt
    rw [Time.deriv_eq, fderiv_fun_sub (hG.const_mul _) (hK.differentiableAt.const_mul _),
      fderiv_const_mul hG, fderiv_const_mul hK.differentiableAt]
    rfl
  have h3 : ∂ₜ (fun s => ∑ j, ∂[j] (A.magneticFieldMatrix 𝓕.c s · (j, i)) x) t
      = ∑ j, ∂[j] (fun y => ∂ₜ (A.magneticFieldMatrix 𝓕.c · y (j, i)) t) x := by
    rw [Time.deriv_fun_sum Finset.univ (fun j s => ∂[j] (A.magneticFieldMatrix 𝓕.c s · (j, i)) x)
      (fun j _ => (hBt j).differentiableAt)]
    exact Finset.sum_congr rfl fun j _ => Space.time_deriv_comm_space_deriv (hBm j) t x
  have hg : (fun y => ∑ j, ∂[j] (A.electricField 𝓕.c t · j) y)
      = 𝓕.ε₀⁻¹ • fun y => J.chargeDensity 𝓕.c t y := by
    funext y
    show (∇ ⬝ A.electricField 𝓕.c t) y = 𝓕.ε₀⁻¹ * J.chargeDensity 𝓕.c t y
    rw [(isExtrema_iff_gauss_ampere_magneticFieldMatrix hA J hJ).mp h t y |>.1, div_eq_mul_inv, mul_comm]
  have hdiv : ∑ j, ∂[i] (∂[j] (A.electricField 𝓕.c t · j)) x
      = ∂[i] (fun y => ∑ j, ∂[j] (A.electricField 𝓕.c t · j) y) x := by
    conv_rhs => rw [Space.deriv_eq_fderiv_basis]
    rw [fderiv_fun_sum (fun j _ => (hEd j j).differentiableAt)]
    simp only [FunLike.coe_sum, Finset.sum_apply, ← Space.deriv_eq_fderiv_basis]
  have hρ : ∂[i] (fun y => ∑ j, ∂[j] (A.electricField 𝓕.c t · j) y) x
      = 𝓕.ε₀⁻¹ * ∂[i] (J.chargeDensity 𝓕.c t ·) x := by
    rw [hg, Space.deriv_const_smul 𝓕.ε₀⁻¹
      (LorentzCurrentDensity.chargeDensity_differentiable_space (hJ.differentiable (by decide)) t),
      Pi.smul_apply, smul_eq_mul]
  have h4 : ∑ j, ∂[j] (fun y => ∂ₜ (A.magneticFieldMatrix 𝓕.c · y (j, i)) t) x
      = ∑ j, ∂[j] (∂[j] (A.electricField 𝓕.c t · i)) x - 𝓕.ε₀⁻¹ * ∂[i] (J.chargeDensity 𝓕.c t ·) x := by
    rw [← hρ, ← hdiv, ← Finset.sum_sub_distrib]
    refine Finset.sum_congr rfl fun j _ => ?_
    rw [show (fun y => ∂ₜ (A.magneticFieldMatrix 𝓕.c · y (j, i)) t)
        = ∂[j] (A.electricField 𝓕.c t · i) - ∂[i] (A.electricField 𝓕.c t · j)
        from funext fun y => time_deriv_magneticFieldMatrix A hA2 t y j i,
      Space.deriv_sub _ _ (hEd i j) (hEd j i), Space.deriv_commute _ (hEs j), Pi.sub_apply]
  rw [h1, h2, h3, h4]
  simp only [div_eq_mul_inv]
  ring