lemma time_deriv_time_deriv_electricField_of_isExtrema {A : ElectromagneticPotential d}
    {𝓕 : FreeSpace}
    (hA : ContDiff ℝ ∞ A) (J : LorentzCurrentDensity d)
    (hJ : ContDiff ℝ ∞ J) (h : IsExtrema 𝓕 A J)
    (t : Time) (x : Space d) (i : Fin d) :
    ∂ₜ (∂ₜ (A.electricField 𝓕.c · x i)) t =
      𝓕.c ^ 2 * ∑ j, (∂[j] (∂[j] (A.electricField 𝓕.c t · i)) x) -
      𝓕.c ^ 2 / 𝓕.ε₀ * ∂[i] (J.chargeDensity 𝓕.c t ·) x -
      𝓕.c ^ 2 * 𝓕.μ₀ * ∂ₜ (J.currentDensity 𝓕.c · x i) t := by
  have hA3 : ContDiff ℝ 3 A := hA.of_le (right_eq_inf.mp rfl)
  have hA2 : ContDiff ℝ 2 A := hA.of_le (right_eq_inf.mp rfl)
  have hEs (j : Fin d) :=
    electricField_apply_contDiff_space (c := 𝓕.c) (i := j) (n := 2) hA3 t
  have hEd (j k : Fin d) := Space.deriv_differentiable (hEs j) k
  have hBm (j : Fin d) := magneticFieldMatrix_contDiff (c := 𝓕.c) (n := 2) A hA3 (j, i)
  have hBt (j : Fin d) := Space.space_deriv_differentiable_time (i := j) (hBm j) x
  have hJt := LorentzCurrentDensity.currentDensity_apply_differentiable_time (c := 𝓕.c)
    (hJ.differentiable (by decide)) x i
  have hg := congrArg (fun f : Space d → ℝ => ∂[i] f x)
    (funext fun y => ((isExtrema_iff_gauss_ampere_magneticFieldMatrix hA J hJ).mp h t y).1)
  unfold Space.div at hg
  rw [Space.deriv_eq_fderiv_basis,
    fderiv_fun_sum (fun j _ => (hEd j j).differentiableAt)] at hg
  simp only [Space.deriv_eq_fderiv_basis, div_eq_mul_inv,
    fderiv_mul_const (LorentzCurrentDensity.chargeDensity_differentiable_space
      (hJ.differentiable (by decide)) t).differentiableAt,
    _root_.sum_apply, _root_.smul_apply, smul_eq_mul] at hg
  simp only [← Space.deriv_eq_fderiv_basis] at hg
  conv_lhs =>
    enter [1, s]
    rw [Time.deriv_euclid (electricField_differentiable_time hA2 x),
      time_deriv_electricField_of_isExtrema hA J hJ h]
  rw [Time.deriv_eq,
    fderiv_fun_sub ((Differentiable.fun_sum fun j _ => hBt j).const_mul _).differentiableAt
      (hJt.const_mul _).differentiableAt,
    fderiv_const_mul (Differentiable.fun_sum fun j _ => hBt j).differentiableAt,
    fderiv_const_mul hJt.differentiableAt,
    fderiv_fun_sum (fun j _ => (hBt j).differentiableAt)]
  simp only [_root_.sub_apply, _root_.smul_apply, _root_.sum_apply, smul_eq_mul,
    ← Time.deriv_eq]
  conv_lhs =>
    enter [1, 2, 2, j]
    rw [Space.time_deriv_comm_space_deriv (hBm j)]
    simp only [time_deriv_magneticFieldMatrix A hA2]
    rw [Space.fun_deriv_sub _ _ (hEd i j) (hEd j i),
      Space.deriv_commute (u := j) (v := i) _ (hEs j)]
  rw [Finset.sum_sub_distrib, hg, FreeSpace.c_sq, mul_comm 𝓕.ε₀ 𝓕.μ₀]
  simp only [one_div, div_eq_mul_inv, mul_inv_rev, mul_sub, mul_assoc,
    inv_mul_cancel₀ 𝓕.μ₀_ne_zero, mul_one]
