lemma time_deriv_time_deriv_electricField_of_isExtrema {A : ElectromagneticPotential d}
    {𝓕 : FreeSpace}
    (hA : ContDiff ℝ ∞ A) (J : LorentzCurrentDensity d)
    (hJ : ContDiff ℝ ∞ J) (h : IsExtrema 𝓕 A J)
    (t : Time) (x : Space d) (i : Fin d) :
    ∂ₜ (∂ₜ (A.electricField 𝓕.c · x i)) t =
      𝓕.c ^ 2 * ∑ j, (∂[j] (∂[j] (A.electricField 𝓕.c t · i)) x) -
      𝓕.c ^ 2 / 𝓕.ε₀ * ∂[i] (J.chargeDensity 𝓕.c t ·) x -
      𝓕.c ^ 2 * 𝓕.μ₀ * ∂ₜ (J.currentDensity 𝓕.c · x i) t := by
  have hA3 : ContDiff ℝ 3 A := hA.of_le (ENat.LEInfty.out)
  have hdJ := hJ.differentiable (by decide)
  have hEs := fun j => electricField_apply_contDiff_space (n := 2) (c := 𝓕.c) (i := j) hA3 t
  have hEd := fun j k => Space.deriv_differentiable (hEs j) k
  have hBc := fun j => magneticFieldMatrix_contDiff (n := 2) (c := 𝓕.c) A
    hA3 (j, i)
  have hBt := fun j => Space.space_deriv_differentiable_time (i := j) (hBc j) x t
  have hJt := LorentzCurrentDensity.currentDensity_apply_differentiable_time
    (c := 𝓕.c) hdJ x i t
  have hgd := congrArg (fun f => fderiv ℝ f x (Space.basis i))
    (funext fun y => ((isExtrema_iff_gauss_ampere_magneticFieldMatrix hA J hJ).mp h t y).1)
  unfold Space.div at hgd
  simp only [div_eq_mul_inv, fderiv_fun_sum (fun j _ => hEd j j x),
    fderiv_mul_const (LorentzCurrentDensity.chargeDensity_differentiable_space
      hdJ t x), _root_.sum_apply, _root_.smul_apply, smul_eq_mul,
    ← Space.deriv_eq_fderiv_basis] at hgd
  conv_lhs =>
    enter [1, s]
    rw [Time.deriv_euclid (electricField_differentiable_time
      (hA.of_le (ENat.LEInfty.out)) x), time_deriv_electricField_of_isExtrema hA J hJ h]
  rw [Time.deriv_eq,
    (((HasFDerivAt.fun_sum fun j _ => (hBt j).hasFDerivAt).const_mul _).fun_sub
      (hJt.hasFDerivAt.const_mul _)).fderiv]
  have hc : (𝓕.c : ℝ) ^ 2 * 𝓕.μ₀ = 1 / 𝓕.ε₀ := by
    rw [FreeSpace.c_sq, div_mul_eq_mul_div₀, mul_div_mul_right _ _ 𝓕.μ₀_ne_zero]
  simp only [_root_.sub_apply, _root_.smul_apply, smul_eq_mul, _root_.sum_apply,
    ← Time.deriv_eq, fun j => Space.time_deriv_comm_space_deriv (i := j) (hBc j) t x,
    time_deriv_magneticFieldMatrix A (hA.of_le (ENat.LEInfty.out)),
    fun j => Space.fun_deriv_sub (u := j) _ _ (hEd i j) (hEd j i),
    fun j => Space.deriv_commute (u := j) (v := i) _ (hEs j),
    Finset.sum_sub_distrib, hgd, mul_sub, ← mul_assoc]
  rw [mul_comm 𝓕.μ₀ 𝓕.ε₀, ← FreeSpace.c_sq]
  simp only [← div_eq_mul_inv, hc]
