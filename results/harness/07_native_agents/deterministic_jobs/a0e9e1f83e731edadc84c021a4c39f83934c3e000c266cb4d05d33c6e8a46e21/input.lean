lemma time_deriv_time_deriv_electricField_of_isExtrema {A : ElectromagneticPotential d}
    {𝓕 : FreeSpace}
    (hA : ContDiff ℝ ∞ A) (J : LorentzCurrentDensity d)
    (hJ : ContDiff ℝ ∞ J) (h : IsExtrema 𝓕 A J)
    (t : Time) (x : Space d) (i : Fin d) :
    ∂ₜ (∂ₜ (A.electricField 𝓕.c · x i)) t =
      𝓕.c ^ 2 * ∑ j, (∂[j] (∂[j] (A.electricField 𝓕.c t · i)) x) -
      𝓕.c ^ 2 / 𝓕.ε₀ * ∂[i] (J.chargeDensity 𝓕.c t ·) x -
      𝓕.c ^ 2 * 𝓕.μ₀ * ∂ₜ (J.currentDensity 𝓕.c · x i) t := by
  have h3 : ContDiff ℝ 3 A := hA.of_le ENat.LEInfty.out
  have hEs : ∀ j, ContDiff ℝ 2 (fun y => A.electricField 𝓕.c t y j) :=
    fun j => electricField_apply_contDiff_space h3 t
  have hdiv : ∂[i] (∇ ⬝ A.electricField 𝓕.c t) x =
      ∑ j, ∂[j] (∂[i] (A.electricField 𝓕.c t · j)) x := by
    unfold Space.div
    rw [Space.deriv_eq, fderiv_fun_sum fun j _ => Space.deriv_differentiable (hEs j) j x,
      _root_.sum_apply]
    exact Finset.sum_congr rfl fun j _ => congrFun (Space.deriv_commute _ (hEs j)) x
  rw [show ∇ ⬝ A.electricField 𝓕.c t = 𝓕.ε₀⁻¹ • J.chargeDensity 𝓕.c t from
    funext fun y => ((isExtrema_iff_gauss_ampere_magneticFieldMatrix hA J hJ).1 h t y).1.trans
      (div_eq_inv_mul _ _), Space.deriv_const_smul _
      (LorentzCurrentDensity.chargeDensity_differentiable_space (hJ.differentiable (by decide)) t)]
    at hdiv
  rw [(funext fun s => (Time.deriv_euclid (electricField_differentiable_time
      (hA.of_le ENat.LEInfty.out) x) s).trans (time_deriv_electricField_of_isExtrema hA J hJ h s x i) :
      ∂ₜ (A.electricField 𝓕.c · x i) = _),
    Time.deriv_eq, (((HasFDerivAt.fun_sum fun j _ => (Space.space_deriv_differentiable_time (i := j)
      (magneticFieldMatrix_contDiff _ h3 (j, i)) x t).hasFDerivAt).const_mul _).fun_sub
      ((LorentzCurrentDensity.currentDensity_apply_differentiable_time
        (hJ.differentiable (by decide)) x i t).hasFDerivAt.const_mul _)).fderiv]
  simp only [ContinuousLinearMap.sub_apply, ContinuousLinearMap.smul_apply, _root_.sum_apply,
    smul_eq_mul, ← Time.deriv_eq, Space.time_deriv_comm_space_deriv (magneticFieldMatrix_contDiff _ h3 _),
    time_deriv_magneticFieldMatrix _ (hA.of_le ENat.LEInfty.out),
    Space.fun_deriv_sub, Space.deriv_differentiable (hEs _) _, Pi.sub_apply, Finset.sum_sub_distrib,
    ← hdiv, Pi.smul_apply, FreeSpace.c_sq, one_div_mul_eq_div, div_mul_cancel_right₀ 𝓕.μ₀_ne_zero]
  ring