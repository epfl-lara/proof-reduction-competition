lemma time_deriv_time_deriv_electricField_of_isExtrema {A : ElectromagneticPotential d}
    {𝓕 : FreeSpace}
    (hA : ContDiff ℝ ∞ A) (J : LorentzCurrentDensity d)
    (hJ : ContDiff ℝ ∞ J) (h : IsExtrema 𝓕 A J)
    (t : Time) (x : Space d) (i : Fin d) :
    ∂ₜ (∂ₜ (A.electricField 𝓕.c · x i)) t =
      𝓕.c ^ 2 * ∑ j, (∂[j] (∂[j] (A.electricField 𝓕.c t · i)) x) -
      𝓕.c ^ 2 / 𝓕.ε₀ * ∂[i] (J.chargeDensity 𝓕.c t ·) x -
      𝓕.c ^ 2 * 𝓕.μ₀ * ∂ₜ (J.currentDensity 𝓕.c · x i) t := by
  have h2c : ContDiff ℝ 2 A := hA.of_le (by decide)
  have h3c : ContDiff ℝ 3 A := hA.of_le (by decide)
  have hB : ∀ j, Differentiable ℝ (fun s => ∂[j] (A.magneticFieldMatrix 𝓕.c s · (j,i)) x) :=
    fun j => Space.space_deriv_differentiable_time (i := j) (magneticFieldMatrix_contDiff A h3c (j,i)) x
  have hC : ∀ j, ContDiff ℝ 2 (fun y => A.electricField 𝓕.c t y j) :=
    fun j => electricField_apply_contDiff_space (i := j) h3c t
  have hE : ∀ j k, Differentiable ℝ (∂[k] fun y => A.electricField 𝓕.c t y j) :=
    fun j k => Space.deriv_differentiable (hC j) k
  have hlin : ∀ (f g : Time → ℝ) (a b : ℝ), DifferentiableAt ℝ f t → DifferentiableAt ℝ g t →
      ∂ₜ (fun s => a * f s - b * g s) t = a * ∂ₜ f t - b * ∂ₜ g t := by
    intro f g a b hf hg
    rw [Time.deriv_eq, fderiv_fun_sub (hf.const_mul a) (hg.const_mul b),
      fderiv_const_mul hf a, fderiv_const_mul hg b]
    simp only [FunLike.coe_sub, FunLike.coe_smul, Pi.sub_apply, Pi.smul_apply, smul_eq_mul, ← Time.deriv_eq]
  have ham : ∂ₜ (A.electricField 𝓕.c · x i) = fun s => 1 / (𝓕.μ₀ * 𝓕.ε₀) *
      ∑ j, ∂[j] (A.magneticFieldMatrix 𝓕.c s · (j,i)) x - 1 / 𝓕.ε₀ * J.currentDensity 𝓕.c s x i := by
    funext s
    rw [Time.deriv_euclid (electricField_differentiable_time h2c x)]
    exact time_deriv_electricField_of_isExtrema hA J hJ h s x i
  have hc : ∀ j, ∂ₜ (fun s => ∂[j] (A.magneticFieldMatrix 𝓕.c s · (j,i)) x) t
      = ∂[j] (∂[j] (A.electricField 𝓕.c t · i)) x - ∂[j] (∂[i] (A.electricField 𝓕.c t · j)) x := by
    intro j
    rw [Space.time_deriv_comm_space_deriv (magneticFieldMatrix_contDiff A h3c (j,i))]
    simp only [time_deriv_magneticFieldMatrix A h2c]
    rw [Space.deriv_eq_fderiv_basis,
      fderiv_fun_sub (hE i j).differentiableAt (hE j i).differentiableAt]
    rfl
  have hg : (fun y => ∑ j, ∂[j] (A.electricField 𝓕.c t · j) y) = 𝓕.ε₀⁻¹ • J.chargeDensity 𝓕.c t := by
    funext y
    simp only [Pi.smul_apply, smul_eq_mul]
    exact ((isExtrema_iff_gauss_ampere_magneticFieldMatrix hA J hJ).1 h t y).1.trans
      (by rw [div_eq_mul_inv, mul_comm])
  have hs : ∂[i] (fun y => ∑ j, ∂[j] (A.electricField 𝓕.c t · j) y) x
      = ∑ j, ∂[i] (∂[j] (A.electricField 𝓕.c t · j)) x := by
    rw [Space.deriv_eq_fderiv_basis, fderiv_fun_sum fun j _ => (hE j j).differentiableAt]
    simp only [_root_.sum_apply, ← Space.deriv_eq_fderiv_basis]

  rw [ham, hlin _ _ _ _ (Differentiable.fun_sum fun j _ => hB j).differentiableAt
    (LorentzCurrentDensity.currentDensity_apply_differentiable_time (hJ.differentiable (by decide)) x i t),
    Time.deriv_fun_sum Finset.univ _ fun j _ => (hB j).differentiableAt,
    Finset.sum_congr rfl fun j _ => hc j, Finset.sum_sub_distrib,
    Finset.sum_congr rfl fun j _ => congrFun (Space.deriv_commute _ (hC j)) x,
    ← hs, hg, Space.deriv_const_smul _
      (LorentzCurrentDensity.chargeDensity_differentiable_space (hJ.differentiable (by decide)) t),
    Pi.smul_apply, smul_eq_mul]
  have hμ : 1 / 𝓕.ε₀ = 𝓕.c ^ 2 * 𝓕.μ₀ := by
    rw [FreeSpace.c_sq]
    field_simp
  rw [← hμ, mul_sub, ← mul_assoc, FreeSpace.c_sq, mul_comm 𝓕.μ₀ 𝓕.ε₀]
  simp only [div_eq_mul_inv]