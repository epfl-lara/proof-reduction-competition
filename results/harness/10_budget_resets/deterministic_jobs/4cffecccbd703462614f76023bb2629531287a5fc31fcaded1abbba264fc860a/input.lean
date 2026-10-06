lemma time_deriv_time_deriv_electricField_of_isExtrema {A : ElectromagneticPotential d}
    {𝓕 : FreeSpace}
    (hA : ContDiff ℝ ∞ A) (J : LorentzCurrentDensity d)
    (hJ : ContDiff ℝ ∞ J) (h : IsExtrema 𝓕 A J)
    (t : Time) (x : Space d) (i : Fin d) :
    ∂ₜ (∂ₜ (A.electricField 𝓕.c · x i)) t =
      𝓕.c ^ 2 * ∑ j, (∂[j] (∂[j] (A.electricField 𝓕.c t · i)) x) -
      𝓕.c ^ 2 / 𝓕.ε₀ * ∂[i] (J.chargeDensity 𝓕.c t ·) x -
      𝓕.c ^ 2 * 𝓕.μ₀ * ∂ₜ (J.currentDensity 𝓕.c · x i) t := by
  have hA3 : ContDiff ℝ 3 A := hA.of_le ENat.LEInfty.out
  have hEs := fun j => electricField_apply_contDiff_space (n := 2) (c := 𝓕.c) (i := j)
    hA3 t
  have hEd := fun j k => Space.deriv_differentiable (hEs j) k
  have hB := fun j => magneticFieldMatrix_contDiff (n := 2) (c := 𝓕.c) A
    hA3 (j, i)
  have hg := congrArg (fun f : _ → ℝ => fderiv ℝ f x (Space.basis i))
    (funext (fun y => ((isExtrema_iff_gauss_ampere_magneticFieldMatrix hA J hJ).mp h t y).1))
  unfold Space.div at hg
  simp only [div_eq_mul_inv, fderiv_fun_sum (fun j _ => (hEd j j).differentiableAt),
    fderiv_mul_const (LorentzCurrentDensity.chargeDensity_differentiable_space
      (hJ.differentiable (by decide)) t).differentiableAt,
    _root_.sum_apply, _root_.smul_apply, smul_eq_mul, ← Space.deriv_eq] at hg
  conv_lhs =>
    enter [1]
    ext s
    rw [Time.deriv_euclid (electricField_differentiable_time
      (hA.of_le ENat.LEInfty.out) x), time_deriv_electricField_of_isExtrema hA J hJ h]
  rw [Time.deriv_eq,
    (((HasFDerivAt.fun_sum (fun j _ =>
      (Space.space_deriv_differentiable_time (hB j) x t).hasFDerivAt)).const_mul
      _).fun_sub ((LorentzCurrentDensity.currentDensity_apply_differentiable_time
        (hJ.differentiable (by decide)) x i t).hasFDerivAt.const_mul _)).fderiv]
  simp only [_root_.sub_apply, _root_.smul_apply, _root_.sum_apply, smul_eq_mul,
    ← Time.deriv_eq, fun j => Space.time_deriv_comm_space_deriv (i := j) (hB j) t x,
    time_deriv_magneticFieldMatrix A (hA.of_le ENat.LEInfty.out),
    fun j => Space.fun_deriv_sub (u := j) _ _ (hEd i j) (hEd j i),
    fun j => Space.deriv_commute (u := j) (v := i) _ (hEs j),
    Pi.sub_apply, Finset.sum_sub_distrib, hg, mul_sub, ← mul_assoc,
    FreeSpace.c_sq, mul_comm 𝓕.μ₀ 𝓕.ε₀, ← div_eq_mul_inv,
    ← div_div, div_mul_cancel₀ _ 𝓕.μ₀_ne_zero]